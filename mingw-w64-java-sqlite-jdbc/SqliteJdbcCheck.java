/* SPDX-License-Identifier: MIT */
import java.sql.*;

/** Functional check of the packaged driver: native library, SQL features and file I/O. */
public class SqliteJdbcCheck {
    public static void main(String[] args) throws Exception {
        String file = args[0], sqliteVersion = args[1];
        try (Connection c = DriverManager.getConnection("jdbc:sqlite:" + file);
             Statement s = c.createStatement()) {
            require(org.sqlite.SQLiteJDBCLoader.isNativeMode(), "native mode");
            require(c.getMetaData().getDriverName().equals("SQLite JDBC"), "driver name");
            require(query(s, "SELECT sqlite_version()").equals(sqliteVersion), "SQLite version");
            require(query(s, "SELECT sqlite_compileoption_used('JDBC_EXTENSIONS')").equals("1"), "JDBC_EXTENSIONS");
            s.executeUpdate("CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT, v REAL)");
            try (PreparedStatement p = c.prepareStatement("INSERT INTO t(name, v) VALUES (?, ?)")) {
                for (int i = 1; i <= 10; i++) {
                    p.setString(1, "row" + i);
                    p.setDouble(2, i * 1.5);
                    p.addBatch();
                }
                p.executeBatch();
            }
            require(query(s, "SELECT count(*) FROM t").equals("10"), "batch insert");
            // UPDATE/DELETE ... LIMIT (generated parser with --update-limit)
            s.executeUpdate("DELETE FROM t WHERE id > 5 ORDER BY id LIMIT 2");
            require(query(s, "SELECT count(*) FROM t").equals("8"), "DELETE LIMIT");
            // math functions and the linked-in extension functions
            require(query(s, "SELECT sqrt(16)").equals("4.0"), "math");
            require(query(s, "SELECT reverse('abc')").equals("cba"), "extension functions");
            // FTS5, R*Tree and JSON
            s.executeUpdate("CREATE VIRTUAL TABLE f USING fts5(body)");
            s.executeUpdate("INSERT INTO f VALUES ('hello sqlite world')");
            require(query(s, "SELECT count(*) FROM f WHERE f MATCH 'sqlite'").equals("1"), "FTS5");
            s.executeUpdate("CREATE VIRTUAL TABLE r USING rtree(id, x0, x1)");
            require(query(s, "SELECT json_extract('{\"a\":42}', '$.a')").equals("42"), "JSON");
            // column metadata (SQLITE_ENABLE_COLUMN_METADATA)
            try (ResultSet rs = s.executeQuery("SELECT name FROM t")) {
                require(rs.getMetaData().getTableName(1).equals("t"), "column metadata");
            }
        }
        try (Connection c = DriverManager.getConnection("jdbc:sqlite:" + file);
             Statement s = c.createStatement()) {
            require(query(s, "SELECT sum(v) FROM t").equals(String.valueOf(1.5 * (1 + 2 + 3 + 4 + 5 + 8 + 9 + 10))), "persistence");
        }
        System.out.println("PASS: SQLite JDBC native driver");
    }

    static String query(Statement s, String sql) throws SQLException {
        try (ResultSet rs = s.executeQuery(sql)) {
            rs.next();
            return rs.getString(1);
        }
    }

    static void require(boolean condition, String name) {
        if (!condition) throw new AssertionError("SQLite JDBC check failed: " + name);
    }
}
