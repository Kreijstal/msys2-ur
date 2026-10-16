/*
 * Merges jars into one while moving packages, like maven-shade-plugin's
 * <relocations>: class names in the bytecode (via ASM's ClassRemapper),
 * class-name and path strings that start with a relocated prefix, and the
 * entry names are rewritten.  module-info.class and manifests are dropped;
 * the first of duplicate entries wins.  Compiled by jb_relocate against the
 * packaged ASM.
 *
 * usage: java jb.Relocate OUT.jar [-r from.package=to.package]... IN.jar...
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package jb;

import java.io.*;
import java.util.*;
import java.util.jar.*;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.commons.ClassRemapper;
import org.objectweb.asm.commons.Remapper;

public class Relocate {
    static final List<String[]> RULES = new ArrayList<>();   // internal names: from/, to/

    static String reloc(String s, char sep) {
        for (String[] r : RULES) {
            String from = r[0].replace('/', sep), to = r[1].replace('/', sep);
            if (s.startsWith(from)) {
                return to + s.substring(from.length());
            }
        }
        return null;
    }

    static final Remapper REMAPPER = new Remapper() {
        @Override
        public String map(String internalName) {
            String r = reloc(internalName, '/');
            return r == null ? internalName : r;
        }

        @Override
        public Object mapValue(Object value) {
            if (value instanceof String) {
                String s = (String) value;
                String r = reloc(s, '.');
                if (r == null) {
                    r = reloc(s, '/');
                }
                return r == null ? s : r;
            }
            return super.mapValue(value);
        }
    };

    public static void main(String[] args) throws Exception {
        String out = args[0];
        List<String> ins = new ArrayList<>();
        for (int i = 1; i < args.length; i++) {
            if (args[i].equals("-r")) {
                String[] r = args[++i].split("=", 2);
                RULES.add(new String[] {r[0].replace('.', '/') + "/", r[1].replace('.', '/') + "/"});
            } else {
                ins.add(args[i]);
            }
        }
        Set<String> seen = new HashSet<>();
        int classes = 0;
        try (JarOutputStream jo = new JarOutputStream(new FileOutputStream(out))) {
            for (String in : ins) {
                try (JarFile jf = new JarFile(in)) {
                    for (JarEntry e : Collections.list(jf.entries())) {
                        String n = e.getName();
                        if (e.isDirectory() || n.equals("META-INF/MANIFEST.MF")
                                || n.endsWith("module-info.class") || n.startsWith("META-INF/maven/")) {
                            continue;
                        }
                        byte[] data;
                        try (InputStream is = jf.getInputStream(e)) {
                            data = is.readAllBytes();
                        }
                        String name = n;
                        if (n.endsWith(".class")) {
                            ClassReader cr = new ClassReader(data);
                            ClassWriter cw = new ClassWriter(0);
                            cr.accept(new ClassRemapper(cw, REMAPPER), 0);
                            data = cw.toByteArray();
                            classes++;
                        }
                        String prefix = n.startsWith("META-INF/versions/")
                                ? n.substring(0, n.indexOf('/', "META-INF/versions/".length()) + 1) : "";
                        String r = reloc(n.substring(prefix.length()), '/');
                        if (r != null) {
                            name = prefix + r;
                        }
                        if (!seen.add(name)) {
                            continue;
                        }
                        jo.putNextEntry(new JarEntry(name));
                        jo.write(data);
                        jo.closeEntry();
                    }
                }
            }
        }
        System.out.println("Relocate: " + out + ": " + classes + " classes from " + ins.size() + " jars");
    }
}
