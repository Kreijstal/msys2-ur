/*
 * Runs Modello the way modello-maven-plugin does, without Maven: unlike
 * org.codehaus.modello.ModelloCli it passes the plugin's default
 * parameters (domAsXpp3, the "Ex" suffix of extended writers, encoding,
 * javaSource) and any extra key=value parameters.  Modello is called
 * reflectively, so this class needs no Modello at compile time.
 *
 * usage: java jb.ModelloRunner MODEL OUTPUT-TYPE OUTPUT-DIR VERSION [key=value]...
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package jb;

import java.io.File;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.HashMap;
import java.util.Map;

public class ModelloRunner {
    public static void main(String[] args) throws Exception {
        if (args.length < 4) {
            System.err.println("usage: ModelloRunner MODEL OUTPUT-TYPE OUTPUT-DIR VERSION [key=value]...");
            System.exit(2);
        }
        Map<String, Object> p = new HashMap<>();
        p.put("modello.output.directory", new File(args[2]).getAbsolutePath());
        p.put("modello.version", args[3]);
        p.put("modello.package.with.version", "false");
        p.put("modello.output.java.source", "8");
        p.put("modello.output.encoding", "UTF-8");
        p.put("modello.dom.xpp3", "true");
        p.put("modello.xpp3.extended.suffix", "Ex");
        for (int i = 4; i < args.length; i++) {
            int eq = args[i].indexOf('=');
            p.put(args[i].substring(0, eq), args[i].substring(eq + 1));
        }
        Class<?> modello = Class.forName("org.codehaus.modello.Modello");
        Object m = modello.getConstructor().newInstance();
        try (Reader r = new InputStreamReader(Files.newInputStream(new File(args[0]).toPath()),
                StandardCharsets.UTF_8)) {
            modello.getMethod("generate", Reader.class, String.class, Map.class).invoke(m, r, args[1], p);
        }
    }
}
