/*
 * Smoke test for a built jar: loads every class it contains (without running
 * static initialisers) and resolves the signatures of its fields, methods and
 * constructors, so missing dependencies or a broken classpath show up as
 * NoClassDefFoundError.
 *
 * usage: java jb.LoadCheck [--ignore REGEX] JAR [CLASSPATH]
 *   REGEX matches class names whose failures are expected (optional
 *   dependencies that are not packaged).
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package jb;

import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.*;
import java.util.jar.*;
import java.util.regex.Pattern;

public class LoadCheck {
    public static void main(String[] args) throws Exception {
        Pattern ignore = null;
        int i = 0;
        if (args.length > 1 && args[0].equals("--ignore")) {
            ignore = Pattern.compile(args[1]);
            i = 2;
        }
        File jar = new File(args[i]);
        List<URL> urls = new ArrayList<>();
        urls.add(jar.toURI().toURL());
        if (args.length > i + 1) {
            for (String p : args[i + 1].split(File.pathSeparator)) {
                if (!p.isEmpty()) {
                    urls.add(new File(p).toURI().toURL());
                }
            }
        }
        int ok = 0, ignored = 0;
        List<String> failed = new ArrayList<>();
        try (URLClassLoader cl = new URLClassLoader(urls.toArray(new URL[0]),
                    ClassLoader.getPlatformClassLoader());
             JarFile jf = new JarFile(jar)) {
            for (JarEntry e : Collections.list(jf.entries())) {
                String n = e.getName();
                if (!n.endsWith(".class") || n.startsWith("META-INF/")
                        || n.endsWith("module-info.class") || n.endsWith("package-info.class")) {
                    continue;
                }
                String cn = n.substring(0, n.length() - 6).replace('/', '.');
                try {
                    Class<?> c = Class.forName(cn, false, cl);
                    c.getDeclaredFields();
                    c.getDeclaredMethods();
                    c.getDeclaredConstructors();
                    ok++;
                } catch (Throwable t) {
                    if (ignore != null && ignore.matcher(cn).find()) {
                        ignored++;
                    } else {
                        failed.add(cn + ": " + t);
                    }
                }
            }
        }
        for (String f : failed) {
            System.err.println("LoadCheck: FAILED " + f);
        }
        System.out.println("LoadCheck: " + jar.getName() + ": " + ok + " classes loaded"
                + (ignored > 0 ? ", " + ignored + " ignored" : "")
                + (failed.isEmpty() ? "" : ", " + failed.size() + " FAILED"));
        if (ok == 0 && failed.isEmpty() && ignored == 0) {
            System.out.println("LoadCheck: (no classes)");
        }
        System.exit(failed.isEmpty() ? 0 : 1);
    }
}
