/* SPDX-License-Identifier: MIT */
import org.osgi.framework.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.locationtech.jts.io.WKTReader;
import org.apache.commons.jexl3.JexlBuilder;
import org.apache.commons.dbcp2.BasicDataSource;
import org.eclipse.jetty.server.Server;
import org.jfree.chart.ChartFactory;
import org.jfree.chart.ChartUtils;
import org.jfree.data.category.DefaultCategoryDataset;
import java.io.*;

public class OsgiChecks implements BundleActivator {
    public void start(BundleContext context) throws Exception {
        Thread thread = Thread.currentThread();
        ClassLoader previous = thread.getContextClassLoader();
        thread.setContextClassLoader(getClass().getClassLoader());
        try {
            require(net.sf.jsqlparser.parser.CCJSqlParserUtil.parse("SELECT 42").toString().equals("SELECT 42"), "SQL");
            require(((Number) new JexlBuilder().create().createExpression("6 * 7").evaluate(null)).intValue() == 42, "JEXL");
            require(new WKTReader().read("POINT (1 2)").getCoordinate().x == 1, "GIS");
            require(new org.cugos.wkg.WKTWriter().write(new org.cugos.wkg.WKTReader().read("POINT (1 2)")).contains("1"), "WKG");
            byte[] xlsx;
            try (var book = new XSSFWorkbook(); var bytes = new ByteArrayOutputStream()) {
                book.createSheet("data").createRow(0).createCell(0).setCellValue(42);
                book.write(bytes); xlsx = bytes.toByteArray();
            }
            try (var book = new XSSFWorkbook(new ByteArrayInputStream(xlsx))) {
                require(book.getSheetAt(0).getRow(0).getCell(0).getNumericCellValue() == 42, "XLSX");
            }
            require(new graphql.schema.idl.SchemaParser().parse("type Query { answer: Int }").getType("Query").isPresent(), "GraphQL");
            var data = new DefaultCategoryDataset(); data.addValue(42, "series", "answer");
            var bytes = new ByteArrayOutputStream();
            ChartUtils.writeChartAsPNG(bytes, ChartFactory.createBarChart("test", "x", "y", data), 200, 100);
            require(bytes.size() > 500, "chart PNG");
            try (var pool = new BasicDataSource(); var ssh = new net.schmizz.sshj.SSHClient()) {
                require(pool.getMaxTotal() > 0, "DBCP");
                require(!ssh.getTransport().getConfig().getKeyExchangeFactories().isEmpty(), "SSHJ");
            }
            var key = com.jcraft.jsch.KeyPair.genKeyPair(new com.jcraft.jsch.JSch(), com.jcraft.jsch.KeyPair.RSA, 2048);
            require(key.getPublicKeyBlob().length > 200, "JSch"); key.dispose();
            Server server = new Server(); server.start(); server.stop();
            require(org.slf4j.LoggerFactory.getILoggerFactory().getClass().getName().equals("ch.qos.logback.classic.LoggerContext"), "SLF4J Logback provider");
            org.slf4j.LoggerFactory.getLogger(OsgiChecks.class).info("DBeaver dependency logging check");
            System.out.println("PASS: SQL, JEXL, GIS/WKG, XLSX, GraphQL, chart, pooling, SSH and Jetty inside Equinox");
        } finally { thread.setContextClassLoader(previous); }
    }
    static void require(boolean condition, String name) {
        if (!condition) throw new AssertionError("OSGi " + name);
    }
    public void stop(BundleContext context) { }
}
