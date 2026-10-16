/*
 * Runs JUnit 4 test classes with some tests excluded (tests that cannot pass
 * on this platform or JDK, e.g. ones that install a SecurityManager).
 * Compiled against the packaged JUnit by jb_junit4 at check() time.
 *
 * usage: java jb.JUnit4Runner [-auto] [-x Class[#methodRegex]]... TestClass...
 *   Class is a fully qualified or simple class name.  With -auto the given
 *   classes are candidates: abstract ones and ones without tests are skipped.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package jb;

import java.util.*;
import java.util.regex.Pattern;
import org.junit.internal.TextListener;
import org.junit.runner.Description;
import org.junit.runner.JUnitCore;
import org.junit.runner.Request;
import org.junit.runner.Result;
import org.junit.runner.manipulation.Filter;

public class JUnit4Runner {
    static boolean isTest(Class<?> c) {
        int m = c.getModifiers();
        if (c.isInterface() || java.lang.reflect.Modifier.isAbstract(m)
                || !java.lang.reflect.Modifier.isPublic(m)) {
            return false;
        }
        if (c.isAnnotationPresent(org.junit.runner.RunWith.class)
                || junit.framework.Test.class.isAssignableFrom(c)) {
            return true;
        }
        for (Class<?> k = c; k != null; k = k.getSuperclass()) {
            for (java.lang.reflect.Method meth : k.getDeclaredMethods()) {
                if (meth.isAnnotationPresent(org.junit.Test.class)) {
                    return true;
                }
            }
        }
        return false;
    }

    public static void main(String[] args) throws Exception {
        final List<String[]> excludes = new ArrayList<>();
        List<Class<?>> classes = new ArrayList<>();
        boolean auto = false;
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("-auto")) {
                auto = true;
            } else if (args[i].equals("-x")) {
                String x = args[++i];
                int h = x.indexOf('#');
                excludes.add(h < 0 ? new String[] {x, null}
                        : new String[] {x.substring(0, h), x.substring(h + 1)});
            } else {
                Class<?> c = Class.forName(args[i]);
                if (!auto || isTest(c)) {
                    classes.add(c);
                }
            }
        }
        System.out.println("JUnit4Runner: " + classes.size() + " test classes");
        Filter filter = new Filter() {
            @Override
            public boolean shouldRun(Description d) {
                String cls = d.getClassName();
                String m = d.getMethodName();
                for (String[] x : excludes) {
                    boolean classMatch = cls != null && (cls.equals(x[0])
                            || cls.endsWith("." + x[0]) || cls.endsWith("$" + x[0]));
                    if (!classMatch) {
                        continue;
                    }
                    if (x[1] == null) {
                        return false;
                    }
                    if (m != null && Pattern.compile(x[1]).matcher(m).lookingAt()) {
                        return false;
                    }
                }
                return true;
            }

            @Override
            public String describe() {
                return "javabuild excludes";
            }
        };
        JUnitCore core = new JUnitCore();
        core.addListener(new TextListener(System.out));
        Request req = Request.classes(classes.toArray(new Class<?>[0]));
        if (!excludes.isEmpty()) {
            req = req.filterWith(filter);
        }
        Result r = core.run(req);
        System.exit(r.wasSuccessful() ? 0 : 1);
    }
}
