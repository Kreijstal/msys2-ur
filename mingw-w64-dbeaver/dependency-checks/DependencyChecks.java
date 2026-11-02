/* SPDX-License-Identifier: MIT */
import java.io.*;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.apache.commons.dbcp2.BasicDataSource;
import org.apache.commons.jexl3.*;
import org.ejml.data.*;
import org.ejml.dense.row.CommonOps_DDRM;
import org.ejml.ops.MatrixIO;
import org.locationtech.jts.geom.*;
import org.locationtech.jts.io.*;
import org.jfree.chart.*;
import org.jfree.data.category.DefaultCategoryDataset;
import org.eclipse.jetty.server.*;
import org.eclipse.jetty.util.Callback;
import net.sf.saxon.s9api.*;
import org.sat4j.core.VecInt;
import org.sat4j.specs.*;

public class DependencyChecks {
    static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    static void passed(String name) { System.out.println("PASS: " + name); }
    public static void main(String[] args) throws Exception {
        Path temp = Files.createTempDirectory("dbeaver-dependencies-");
        try {
            String sql = "SELECT id, name FROM users WHERE id = 42";
            require(net.sf.jsqlparser.parser.CCJSqlParserUtil.parse(sql).toString().contains("42"), "SQL parser");
            JexlContext context = new MapContext();
            context.set("x", 6);
            Object result = new JexlBuilder().create().createExpression("x * 7").evaluate(context);
            require(((Number) result).intValue() == 42, "JEXL expression");
            passed("SQL parsing and JEXL evaluation");

            try (BasicDataSource pool = new BasicDataSource()) {
                pool.setUrl("jdbc:h2:mem:bootstrap;DB_CLOSE_DELAY=-1");
                pool.setDriverClassName("org.h2.Driver");
                try (var connection = pool.getConnection(); var statement = connection.createStatement();
                     var rows = statement.executeQuery("SELECT 6 * 7")) {
                    require(rows.next() && rows.getInt(1) == 42, "pooled JDBC query");
                }
                require(pool.getNumActive() == 0, "connection returned to pool");
            }
            passed("DBCP, Pool2 and H2 database query");

            byte[] spreadsheet;
            try (var workbook = new XSSFWorkbook(); var bytes = new ByteArrayOutputStream()) {
                var sheet = workbook.createSheet("data");
                sheet.createRow(0).createCell(0).setCellValue("Grüße");
                sheet.createRow(1).createCell(0).setCellValue(42);
                workbook.write(bytes);
                spreadsheet = bytes.toByteArray();
            }
            try (var workbook = new XSSFWorkbook(new ByteArrayInputStream(spreadsheet))) {
                require(workbook.getSheetAt(0).getRow(0).getCell(0).getStringCellValue().equals("Grüße"), "XLSX Unicode");
                require(workbook.getSheetAt(0).getRow(1).getCell(0).getNumericCellValue() == 42, "XLSX number");
            }
            try (var workbook = com.github.pjfanning.xlsx.StreamingReader.builder()
                    .setSharedStringsImplementationType(com.github.pjfanning.xlsx.SharedStringsImplementationType.TEMP_FILE_BACKED)
                    .open(new ByteArrayInputStream(spreadsheet))) {
                var rows = workbook.getSheetAt(0).iterator();
                require(rows.next().getCell(0).getStringCellValue().equals("Grüße"), "streaming XLSX Unicode");
                require(rows.next().getCell(0).getNumericCellValue() == 42 && !rows.hasNext(), "streaming XLSX number");
            }
            passed("POI XLSX write/read, XMLBeans schemas and temp-backed streaming reader");

            Geometry geometry = new WKTReader().read("POLYGON ((0 0, 3 0, 3 2, 0 2, 0 0))");
            Geometry roundTrip = new WKBReader().read(new WKBWriter().write(geometry));
            require(roundTrip.equalsExact(geometry) && roundTrip.getArea() == 6, "geometry WKB round trip");
            org.cts.CRSFactory crs = new org.cts.CRSFactory();
            crs.getRegistryManager().addRegistry(new org.cts.registry.EPSGRegistry());
            require(crs.getCRS("EPSG:4326").getName().equals("WGS 84"), "EPSG registry data");
            var wkt = new org.cugos.wkg.WKTReader();
            require(new org.cugos.wkg.WKTWriter().write(wkt.read("POINT Z (1 2 3)")).contains("3"), "WKG generated grammar");
            passed("JTS WKT/WKB geometry, CTS EPSG data and generated WKG parser");

            DMatrixRMaj matrix = new DMatrixRMaj(new double[][]{{4, 7}, {2, 6}});
            DMatrixRMaj inverse = new DMatrixRMaj(2, 2);
            require(CommonOps_DDRM.invert(matrix, inverse), "matrix inverse");
            DMatrixRMaj product = new DMatrixRMaj(2, 2);
            CommonOps_DDRM.mult(matrix, inverse, product);
            require(Math.abs(product.get(0, 0) - 1) < 1e-10 && Math.abs(product.get(0, 1)) < 1e-10, "matrix inverse result");
            ComplexPolar_F64 a = new ComplexPolar_F64(2, 1);
            ComplexPolar_F64 b = new ComplexPolar_F64();
            b.setR(a.getR()); b.setTheta(a.getTheta());
            require(a.equals(b) && a.hashCode() == b.hashCode(), "expanded Lombok value methods");
            b.setR(3);
            require(!a.equals(b), "expanded value inequality");
            String matFile = temp.resolve("matrix.mat").toString();
            MatrixIO.saveMatlab(matrix, matFile);
            DMatrixRMaj loaded = MatrixIO.loadMatlab(matFile);
            require(loaded.get(0, 1) == 7 && loaded.get(1, 0) == 2, "MAT adapter round trip");
            passed("EJML inverse, expanded value API and MATLAB adapter round trip");

            var dataset = new DefaultCategoryDataset();
            dataset.addValue(42, "series", "answer");
            var chart = ChartFactory.createBarChart("test", "x", "y", dataset);
            Path png = temp.resolve("chart.png");
            ChartUtils.saveChartAsPNG(png.toFile(), chart, 320, 240);
            byte[] image = Files.readAllBytes(png);
            require(image.length > 500 && image[1] == 'P' && image[2] == 'N' && image[3] == 'G', "chart PNG");
            passed("JFreeChart PNG rendering");

            Processor processor = new Processor(false);
            XdmNode xml = processor.newDocumentBuilder().build(new javax.xml.transform.stream.StreamSource(new StringReader("<root><n>6</n><n>7</n></root>")));
            XPathSelector xpath = processor.newXPathCompiler().compile("sum(/root/n)").load();
            xpath.setContextItem(xml);
            require(xpath.evaluateSingle().getStringValue().equals("13"), "Saxon XPath");
            passed("Saxon native XML tree and XPath evaluation");

            var solver = org.sat4j.minisat.SolverFactory.newDefault();
            solver.newVar(1);
            solver.addClause(new VecInt(new int[]{1}));
            require(solver.isSatisfiable() && solver.model(1), "SAT solution");
            try {
                solver.addClause(new VecInt(new int[]{-1}));
                require(!solver.isSatisfiable(), "UNSAT solution");
            } catch (ContradictionException expected) { }
            passed("SAT4J satisfiable and contradictory constraints");

            var key = com.jcraft.jsch.KeyPair.genKeyPair(new com.jcraft.jsch.JSch(), com.jcraft.jsch.KeyPair.RSA, 2048);
            require(key.getPublicKeyBlob().length > 200, "JSch RSA key");
            var encodedKey = new ByteArrayOutputStream();
            key.writePrivateKey(encodedKey);
            require(encodedKey.toString(java.nio.charset.StandardCharsets.US_ASCII).contains("PRIVATE KEY"), "JSch key serialization");
            key.dispose();
            try (var ssh = new net.schmizz.sshj.SSHClient()) {
                require(!ssh.getTransport().getConfig().getKeyExchangeFactories().isEmpty(), "SSHJ algorithms");
            }
            Security.addProvider(new org.bouncycastle.jce.provider.BouncyCastleProvider());
            var pair = KeyPairGenerator.getInstance("RSA").generateKeyPair();
            Signature signature = Signature.getInstance("SHA256withRSA", "BC");
            signature.initSign(pair.getPrivate()); signature.update(new byte[]{1, 2, 3});
            byte[] signed = signature.sign();
            signature.initVerify(pair.getPublic()); signature.update(new byte[]{1, 2, 3});
            require(signature.verify(signed), "Bouncy Castle signature");
            passed("JSch RSA key, SSHJ configuration and Bouncy Castle signature");

            var types = new graphql.schema.idl.SchemaParser().parse("type Query { answer: Int }");
            var wiring = graphql.schema.idl.RuntimeWiring.newRuntimeWiring()
                .type("Query", builder -> builder.dataFetcher("answer", env -> 42)).build();
            var graph = graphql.GraphQL.newGraphQL(new graphql.schema.idl.SchemaGenerator().makeExecutableSchema(types, wiring)).build();
            var query = graph.execute("{ answer }");
            require(query.getErrors().isEmpty() && query.getData().toString().equals("{answer=42}"), "GraphQL query");
            passed("GraphQL schema, shaded ANTLR/Guava and query execution");

            Server server = new Server();
            ServerConnector connector = new ServerConnector(server);
            connector.setHost("127.0.0.1"); connector.setPort(0); server.addConnector(connector);
            server.setHandler(new Handler.Abstract() {
                @Override public boolean handle(Request request, Response response, Callback callback) {
                    response.getHeaders().put("Content-Type", "text/plain; charset=utf-8");
                    response.write(true, java.nio.ByteBuffer.wrap("42".getBytes(java.nio.charset.StandardCharsets.UTF_8)), callback);
                    return true;
                }
            });
            try {
                server.start();
                try (var client = HttpClient.newHttpClient()) {
                    var response = client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + connector.getLocalPort() + "/")).timeout(java.time.Duration.ofSeconds(10)).build(), HttpResponse.BodyHandlers.ofString());
                    require(response.statusCode() == 200 && response.body().equals("42"), "Jetty HTTP response");
                }
            } finally { server.stop(); }
            passed("Jetty HTTP server and real loopback request");
        } finally {
            try (var paths = Files.walk(temp)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
            }
        }
    }
}
