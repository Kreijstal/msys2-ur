/* SPDX-License-Identifier: MIT */
package org.msys2ur.dbeaver.e2e;

import org.eclipse.core.runtime.Platform;
import org.eclipse.equinox.app.IApplicationContext;
import org.jkiss.dbeaver.headless.DBeaverHeadlessApplication;
import org.jkiss.dbeaver.headless.DBeaverTestPlatform;
import org.jkiss.dbeaver.model.DBPDataSource;
import org.jkiss.dbeaver.model.DBPDataSourceContainer;
import org.jkiss.dbeaver.model.DBPEvaluationContext;
import org.jkiss.dbeaver.model.DBUtils;
import org.jkiss.dbeaver.model.app.DBPDataSourceRegistry;
import org.jkiss.dbeaver.model.app.DBPProject;
import org.jkiss.dbeaver.model.connection.DBPConnectionConfiguration;
import org.jkiss.dbeaver.model.connection.DBPDriver;
import org.jkiss.dbeaver.model.connection.DBPDriverConfigurationType;
import org.jkiss.dbeaver.model.connection.DBPDriverLibrary;
import org.jkiss.dbeaver.model.exec.DBCSession;
import org.jkiss.dbeaver.model.exec.jdbc.JDBCSession;
import org.jkiss.dbeaver.model.impl.jdbc.JDBCUtils;
import org.jkiss.dbeaver.model.runtime.DBRProgressMonitor;
import org.jkiss.dbeaver.model.runtime.VoidProgressMonitor;
import org.jkiss.dbeaver.model.struct.DBSEntity;
import org.jkiss.dbeaver.model.struct.DBSObject;
import org.jkiss.dbeaver.model.struct.DBSObjectContainer;
import org.jkiss.dbeaver.runtime.DBWorkbench;
import org.osgi.framework.Bundle;
import org.osgi.framework.BundleContext;
import org.osgi.framework.FrameworkUtil;
import org.osgi.framework.wiring.FrameworkWiring;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Stream;

/**
 * Runs inside the assembled DBeaver product: checks that every installed
 * bundle resolves, then creates SQLite and H2 connections through DBeaver's
 * data source registry with the packaged drivers and executes SQL.
 */
public class E2EApplication extends DBeaverHeadlessApplication {

    @Override
    public Object start(IApplicationContext context) {
        String result;
        try {
            super.start(context);
            run();
            result = "E2E PASS";
        } catch (Throwable e) {
            e.printStackTrace(System.out);
            result = "E2E FAIL: " + e;
        } finally {
            // stops the platform jobs (navigator event processor), which
            // would otherwise keep the JVM alive after the framework stops
            if (DBWorkbench.isPlatformStarted() && DBWorkbench.getPlatform() instanceof DBeaverTestPlatform platform) {
                platform.dispose();
            }
        }
        System.out.println(result);
        try {
            Files.writeString(Path.of(System.getProperty("e2e.dir"), "result.txt"), result + "\n");
        } catch (Exception e) {
            e.printStackTrace(System.out);
        }
        return result.equals("E2E PASS") ? EXIT_OK : Integer.valueOf(13);
    }

    private void run() throws Exception {
        checkBundles();
        require(Platform.getExtensionRegistry().getExtension("org.eclipse.core.runtime.products",
            "org.jkiss.dbeaver.ui.app.standalone.product") != null, "DBeaver product extension");
        require(Platform.getExtensionRegistry().getExtension("org.eclipse.core.runtime.applications",
            "org.jkiss.dbeaver.ui.app.standalone.standalone") != null, "DBeaver application extension");
        Platform.getBundle("org.jkiss.dbeaver.ui.app.standalone")
            .loadClass("org.jkiss.dbeaver.ui.app.standalone.DBeaverApplication");

        DBRProgressMonitor monitor = new VoidProgressMonitor();
        DBPProject project = DBWorkbench.getPlatform().getWorkspace().getActiveProject();
        require(project != null, "active project");
        DBPDataSourceRegistry registry = project.getDataSourceRegistry();
        Path work = Path.of(System.getProperty("e2e.dir"));

        Path sqlite = work.resolve("e2e.sqlite");
        String sqliteSummary = exercise(monitor, registry, "sqlite_jdbc", "jdbc:sqlite:" + sqlite, sqlite.toString(),
            "SELECT 'SQLite ' || sqlite_version()", "e2e_items");
        require(Files.size(sqlite) > 0, "SQLite database file");
        Path h2 = work.resolve("e2e-h2");
        String h2Summary = exercise(monitor, registry, "h2_embedded_v2", "jdbc:h2:" + h2, h2.toString(),
            "SELECT 'H2 ' || H2VERSION()", "PUBLIC", "E2E_ITEMS");

        registry.flushConfig();
        Path projectDir = project.getAbsolutePath();
        try (Stream<Path> files = Files.walk(projectDir)) {
            require(files.anyMatch(p -> p.getFileName().toString().startsWith("data-sources") && contains(p, "jdbc:sqlite:")),
                "saved data source configuration");
        }
        System.out.println("E2E " + sqliteSummary);
        System.out.println("E2E " + h2Summary);
    }

    private void checkBundles() {
        // the system bundle context, through the (active) runtime bundle
        BundleContext context = FrameworkUtil.getBundle(Platform.class).getBundleContext().getBundle(0).getBundleContext();
        Bundle[] bundles = context.getBundles();
        context.getBundle(0).adapt(FrameworkWiring.class).resolveBundles(Arrays.asList(bundles));
        List<String> unresolved = new ArrayList<>();
        List<String> experimental = new ArrayList<>();
        int dbeaver = 0;
        for (Bundle bundle : bundles) {
            if (bundle.getState() == Bundle.INSTALLED) {
                if (Boolean.parseBoolean(bundle.getHeaders("").get("DBeaver-Experimental"))
                    && !Boolean.getBoolean("dbeaver.experimental")) {
                    // DBeaver keeps these out of resolution with a resolver hook
                    // unless -Ddbeaver.experimental=true (ExperimentalBundles)
                    experimental.add(bundle.getSymbolicName());
                    continue;
                }
                unresolved.add(bundle.getSymbolicName() + " " + bundle.getVersion());
            }
            if (bundle.getSymbolicName().startsWith("org.jkiss.")) {
                dbeaver++;
            }
        }
        for (String name : unresolved) {
            System.out.println("UNRESOLVED " + name);
        }
        require(unresolved.isEmpty(), unresolved.size() + " unresolved bundles: " + unresolved);
        System.out.println("E2E bundles: " + bundles.length + " installed, all resolved; " + dbeaver
            + " org.jkiss bundles; experimental (disabled by DBeaver): " + experimental);
    }

    private String exercise(DBRProgressMonitor monitor, DBPDataSourceRegistry registry, String driverId,
                            String url, String database, String versionQuery, String... tablePath) throws Exception {
        DBPDriver driver = DBWorkbench.getPlatform().getDataSourceProviderRegistry().findDriver(driverId);
        require(driver != null, "driver " + driverId);
        Path install = Path.of(Platform.getInstallLocation().getURL().toURI());
        int jars = 0;
        List<String> driverJars = new ArrayList<>();
        for (DBPDriverLibrary library : driver.getDriverLibraries()) {
            if (library.getType() != DBPDriverLibrary.FileType.jar) {
                continue;
            }
            require(!library.isDownloadable(), driverId + ": downloadable library " + library.getPath());
            Path file = library.getLocalFile();
            require(file != null && Files.exists(file) && file.toAbsolutePath().startsWith(install),
                driverId + ": library " + library.getPath() + " not in the product (" + file + ")");
            jars++;
            driverJars.add(install.relativize(file.toAbsolutePath()).toString().replace('\\', '/'));
        }
        require(jars > 0, driverId + ": no driver libraries");

        DBPConnectionConfiguration configuration = new DBPConnectionConfiguration();
        configuration.setConfigurationType(DBPDriverConfigurationType.URL);
        configuration.setUrl(url);
        configuration.setDatabaseName(database);
        if (!driver.isAnonymousAccess()) {
            configuration.setUserName("sa");
            configuration.setUserPassword("");
        }
        DBPDataSourceContainer container = registry.createDataSource(driver, configuration);
        container.setSavePassword(true);
        registry.addDataSource(container);
        require(container.connect(monitor, true, true), driverId + ": connect");
        String version;
        try (DBCSession session = DBUtils.openUtilSession(monitor, container.getDataSource(), "e2e")) {
            JDBCSession jdbc = (JDBCSession) session;
            JDBCUtils.executeSQL(jdbc, "CREATE TABLE e2e_items(id INTEGER PRIMARY KEY, name VARCHAR(20))");
            JDBCUtils.executeSQL(jdbc, "INSERT INTO e2e_items(id, name) VALUES (?, ?)", 1, "alpha");
            JDBCUtils.executeSQL(jdbc, "INSERT INTO e2e_items(id, name) VALUES (?, ?)", 2, "beta");
            JDBCUtils.executeSQL(jdbc, "INSERT INTO e2e_items(id, name) VALUES (?, ?)", 3, "gamma");
            String total = JDBCUtils.queryString(jdbc, "SELECT COUNT(*) FROM e2e_items WHERE name <> ?", "beta");
            require("2".equals(total), driverId + ": query result " + total);
            version = JDBCUtils.queryString(jdbc, versionQuery);
            if (!jdbc.getAutoCommit()) {
                jdbc.commit();
            }
        }
        // reconnect and find the new table through DBeaver's metadata model
        require(container.disconnect(monitor), driverId + ": disconnect");
        require(container.connect(monitor, true, true), driverId + ": reconnect");
        // The headless platform runs in unit-test mode, where DBeaver skips
        // full metadata list reads; look the table up by name through the model.
        DBSObject table = lookup(monitor, container.getDataSource(), tablePath);
        require(table instanceof DBSEntity, driverId + ": table in metadata model (" + table + ")");
        System.out.println("E2E " + driverId + " metadata: " + DBUtils.getObjectFullName(table, DBPEvaluationContext.UI)
            + " (" + table.getClass().getSimpleName() + ")");
        require(container.disconnect(monitor), driverId + ": final disconnect");
        return driverId + " OK (" + version + ") using " + driverJars;
    }

    private static DBSObject lookup(DBRProgressMonitor monitor, Object root, String... path) throws Exception {
        Object object = root;
        for (String name : path) {
            if (!(object instanceof DBSObjectContainer container)) {
                return null;
            }
            object = container.getChild(monitor, name);
        }
        return object instanceof DBSObject found ? found : null;
    }

    private static boolean contains(Path file, String text) {
        try {
            return Files.isRegularFile(file) && Files.readString(file).contains(text);
        } catch (Exception e) {
            return false;
        }
    }

    private static void require(boolean condition, String what) {
        if (!condition) {
            throw new AssertionError("E2E check failed: " + what);
        }
    }
}
