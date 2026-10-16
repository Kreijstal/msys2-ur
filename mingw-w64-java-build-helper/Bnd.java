/*
 * A small subset of bnd for OSGi metadata of third-party libraries built by
 * javabuild (jb_module -b / jb_wrap): analyses the class files of a bundle
 * and writes its manifest from bnd-style instructions.
 *
 *   java jb.Bnd [-D name=value]... CLASSES-DIR|JAR INSTRUCTIONS OUT-MANIFEST [CLASSPATH]
 *
 * Supported instructions (bnd syntax, properties file with continuations):
 *   Export-Package / -exportcontents   patterns (a.b, a.b.*, !a.b.impl, *) with
 *                                      attributes/directives; version= or else
 *                                      package-info @Version / packageinfo, or
 *                                      -exportversion
 *   Import-Package                     patterns, default '*'; attributes and
 *                                      directives (resolution:=optional) are
 *                                      copied, version ranges are computed from
 *                                      the exporters on CLASSPATH (consumer
 *                                      policy [M.m,M+1); provider policy
 *                                      [M.m,M.m+1) for the bundle's own exports
 *                                      and with provide:=true)
 *   -noee: true                        no osgi.ee Require-Capability
 *   -removeheaders                     headers to drop
 *   ${name} macros from -D or the instructions themselves
 * Every other header is copied.  uses:= directives are computed from the
 * package references, as bnd does.  Headers are written sorted by name.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package jb;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import java.util.zip.*;

public class Bnd {

    // -------------------------------------------------------- class parsing

    static final class ClassInfo {
        String pkg;
        int major;
        Set<String> refs = new TreeSet<>();
        Set<String> api = new TreeSet<>();
        String version; // from package-info @Version
        boolean providerType;
        String name;
        List<String> supers = new ArrayList<>();
    }

    /** referenced packages of a descriptor or generic signature */
    static void desc(String s, Set<String> out) {
        try {
            int i = 0;
            if (s.startsWith("<")) i = formals(s, 0, out);
            while (i < s.length()) {
                char c = s.charAt(i);
                if (c == '(' || c == ')' || c == '^') i++;
                else i = type(s, i, out);
            }
        } catch (RuntimeException e) {
            // not a descriptor
        }
    }

    static int formals(String s, int i, Set<String> out) {
        i++;
        while (s.charAt(i) != '>') {
            i = s.indexOf(':', i);
            while (s.charAt(i) == ':') {
                i++;
                char c = s.charAt(i);
                if (c == 'L' || c == 'T' || c == '[') i = type(s, i, out);
            }
        }
        return i + 1;
    }

    static int type(String s, int i, Set<String> out) {
        char c = s.charAt(i);
        if (c == '[') return type(s, i + 1, out);
        if (c == 'T') return s.indexOf(';', i) + 1;
        if (c != 'L') return i + 1;
        int j = i + 1;
        boolean first = true;
        while (true) {
            int k = j;
            while (";<.".indexOf(s.charAt(k)) < 0) k++;
            if (first) addClass(s.substring(j, k), out);
            first = false;
            j = k;
            if (s.charAt(j) == '<') {
                j++;
                while (s.charAt(j) != '>') {
                    char d = s.charAt(j);
                    if (d == '*') j++;
                    else {
                        if (d == '+' || d == '-') j++;
                        j = type(s, j, out);
                    }
                }
                j++;
            }
            if (s.charAt(j) == '.') { j++; continue; }
            return j + 1; // ';'
        }
    }

    static void addClass(String internal, Set<String> out) {
        if (internal.startsWith("[")) {
            desc(internal, out);
            return;
        }
        int s = internal.lastIndexOf('/');
        if (s > 0) out.add(internal.substring(0, s).replace('/', '.'));
    }

    /** Class file analysis: referenced packages (as bnd counts them) and the
     *  packages of the public API (for uses:). */
    static ClassInfo parse(byte[] b) throws IOException {
        return new Parser(b).run();
    }

    static final class Parser {
        final DataInputStream in;
        Object[] pool;
        int[] tags;
        int[][] idx;
        ClassInfo ci = new ClassInfo();
        String self;

        Parser(byte[] b) {
            in = new DataInputStream(new ByteArrayInputStream(b));
        }

        String utf(int i) { return (String) pool[i]; }
        String cls(int i) { return utf(idx[i][0]); }

        void useClass(int i, boolean api) {
            if (i == 0 || tags[i] != 7) return;
            addClass(cls(i), ci.refs);
            if (api) addClass(cls(i), ci.api);
        }

        ClassInfo run() throws IOException {
            if (in.readInt() != 0xCAFEBABE) throw new IOException("not a class file");
            in.readUnsignedShort();
            ci.major = in.readUnsignedShort();
            int n = in.readUnsignedShort();
            pool = new Object[n];
            tags = new int[n];
            idx = new int[n][];
            for (int i = 1; i < n; i++) {
                int t = in.readUnsignedByte();
                tags[i] = t;
                switch (t) {
                    case 1: pool[i] = in.readUTF(); break;
                    case 3: case 4: in.readInt(); break;
                    case 5: case 6: in.readLong(); i++; break;
                    case 7: case 8: case 16: case 19: case 20: idx[i] = new int[] {in.readUnsignedShort()}; break;
                    case 9: case 10: case 11: case 12: case 17: case 18:
                        idx[i] = new int[] {in.readUnsignedShort(), in.readUnsignedShort()}; break;
                    case 15: idx[i] = new int[] {in.readUnsignedByte(), in.readUnsignedShort()}; break;
                    default: throw new IOException("bad constant pool tag " + t);
                }
            }
            // member references, method types and handles
            for (int i = 1; i < n; i++) {
                switch (tags[i]) {
                    case 9: case 10: case 11:
                        useClass(idx[i][0], false);
                        desc(utf(idx[idx[i][1]][1]), ci.refs);
                        break;
                    case 16:
                        desc(utf(idx[i][0]), ci.refs);
                        break;
                    case 17: case 18:
                        desc(utf(idx[idx[i][1]][1]), ci.refs);
                        break;
                    default:
                }
            }
            int access = in.readUnsignedShort();
            self = cls(in.readUnsignedShort());
            ci.name = self;
            int s = self.lastIndexOf('/');
            ci.pkg = s < 0 ? "" : self.substring(0, s).replace('/', '.');
            boolean pub = (access & 0x0001) != 0;
            int sup = in.readUnsignedShort();
            if (sup != 0) { ci.supers.add(cls(sup)); useClass(sup, pub); }
            int ni = in.readUnsignedShort();
            for (int i = 0; i < ni; i++) {
                int x = in.readUnsignedShort();
                ci.supers.add(cls(x));
                useClass(x, pub);
            }
            for (int k = 0; k < 2; k++) {
                int cnt = in.readUnsignedShort();
                for (int i = 0; i < cnt; i++) {
                    int acc = in.readUnsignedShort();
                    in.readUnsignedShort();
                    boolean api = pub && (acc & 0x0005) != 0;
                    String d = utf(in.readUnsignedShort());
                    desc(d, ci.refs);
                    if (api) desc(d, ci.api);
                    attributes(in, api);
                }
            }
            attributes(in, pub);
            ci.refs.remove(ci.pkg);
            ci.api.remove(ci.pkg);
            return ci;
        }

        void attributes(DataInputStream in, boolean api) throws IOException {
            int cnt = in.readUnsignedShort();
            for (int i = 0; i < cnt; i++) {
                String name = utf(in.readUnsignedShort());
                int len = in.readInt();
                byte[] data = new byte[len];
                in.readFully(data);
                DataInputStream a = new DataInputStream(new ByteArrayInputStream(data));
                switch (name) {
                    case "Signature": {
                        String sg = utf(a.readUnsignedShort());
                        desc(sg, ci.refs);
                        if (api) desc(sg, ci.api);
                        break;
                    }
                    case "Exceptions": {
                        int ne = a.readUnsignedShort();
                        for (int j = 0; j < ne; j++) useClass(a.readUnsignedShort(), api);
                        break;
                    }
                    case "InnerClasses": {
                        int nc = a.readUnsignedShort();
                        for (int j = 0; j < nc; j++) {
                            int inner = a.readUnsignedShort(), outer = a.readUnsignedShort();
                            a.readUnsignedShort();
                            a.readUnsignedShort();
                            useClass(inner, false);
                            useClass(outer, false);
                        }
                        break;
                    }
                    case "EnclosingMethod":
                        useClass(a.readUnsignedShort(), false);
                        break;
                    case "BootstrapMethods": {
                        int nb = a.readUnsignedShort();
                        for (int j = 0; j < nb; j++) {
                            a.readUnsignedShort();
                            int na = a.readUnsignedShort();
                            for (int k = 0; k < na; k++) useClass(a.readUnsignedShort(), false);
                        }
                        break;
                    }
                    // only RUNTIME annotations are references (as in bnd); CLASS
                    // ones are still read for @Version / @ProviderType
                    case "RuntimeVisibleAnnotations":
                    case "RuntimeInvisibleAnnotations": {
                        boolean vis = name.startsWith("RuntimeVisible");
                        int na = a.readUnsignedShort();
                        for (int j = 0; j < na; j++) annotation(a, vis, vis && api);
                        break;
                    }
                    case "RuntimeVisibleParameterAnnotations":
                    case "RuntimeInvisibleParameterAnnotations": {
                        boolean vis = name.startsWith("RuntimeVisible");
                        int np = a.readUnsignedByte();
                        for (int p = 0; p < np; p++) {
                            int na = a.readUnsignedShort();
                            for (int j = 0; j < na; j++) annotation(a, vis, vis && api);
                        }
                        break;
                    }
                    case "Code": {
                        a.readUnsignedShort();
                        a.readUnsignedShort();
                        int cl = a.readInt();
                        byte[] code = new byte[cl];
                        a.readFully(code);
                        code(code);
                        int el = a.readUnsignedShort();
                        for (int j = 0; j < el; j++) {
                            a.readUnsignedShort();
                            a.readUnsignedShort();
                            a.readUnsignedShort();
                            useClass(a.readUnsignedShort(), false);
                        }
                        attributes(a, false);
                        break;
                    }
                    default:
                }
            }
        }

        /** class constants used by instructions (new, checkcast, instanceof, ldc, ...) */
        void code(byte[] c) {
            int pc = 0;
            while (pc < c.length) {
                int op = c[pc] & 0xff;
                switch (op) {
                    case 0x12: // ldc
                        useClass(c[pc + 1] & 0xff, false);
                        pc += 2;
                        break;
                    case 0x13: case 0xbb: case 0xbd: case 0xc0: case 0xc1: // ldc_w new anewarray checkcast instanceof
                        useClass(((c[pc + 1] & 0xff) << 8) | (c[pc + 2] & 0xff), false);
                        pc += 3;
                        break;
                    case 0xc5: // multianewarray
                        useClass(((c[pc + 1] & 0xff) << 8) | (c[pc + 2] & 0xff), false);
                        pc += 4;
                        break;
                    case 0xaa: { // tableswitch
                        int p = (pc + 4) & ~3;
                        int lo = readInt(c, p + 4), hi = readInt(c, p + 8);
                        pc = p + 12 + 4 * (hi - lo + 1);
                        break;
                    }
                    case 0xab: { // lookupswitch
                        int p = (pc + 4) & ~3;
                        int np = readInt(c, p + 4);
                        pc = p + 8 + 8 * np;
                        break;
                    }
                    case 0xc4: // wide
                        pc += (c[pc + 1] & 0xff) == 0x84 ? 6 : 4;
                        break;
                    default:
                        pc += LEN[op];
                }
            }
        }

        static int readInt(byte[] c, int p) {
            return ((c[p] & 0xff) << 24) | ((c[p + 1] & 0xff) << 16) | ((c[p + 2] & 0xff) << 8) | (c[p + 3] & 0xff);
        }

        void annotation(DataInputStream a, boolean ref, boolean api) throws IOException {
            String type = utf(a.readUnsignedShort());
            if (ref) desc(type, ci.refs);
            if (api) desc(type, ci.api);
            int np = a.readUnsignedShort();
            for (int i = 0; i < np; i++) {
                String el = utf(a.readUnsignedShort());
                Object v = elementValue(a, ref, api);
                if (type.equals("Lorg/osgi/annotation/versioning/Version;") && el.equals("value")
                        && self.endsWith("/package-info")) {
                    ci.version = (String) v;
                }
            }
            if (type.equals("Lorg/osgi/annotation/versioning/ProviderType;")) ci.providerType = true;
        }

        Object elementValue(DataInputStream a, boolean ref, boolean api) throws IOException {
            int tag = a.readUnsignedByte();
            switch (tag) {
                case 's': return pool[a.readUnsignedShort()];
                case 'e': {
                    String t = utf(a.readUnsignedShort());
                    if (ref) desc(t, ci.refs);
                    if (api) desc(t, ci.api);
                    a.readUnsignedShort();
                    return null;
                }
                case 'c': {
                    String t = utf(a.readUnsignedShort());
                    if (ref) desc(t, ci.refs);
                    if (api) desc(t, ci.api);
                    return null;
                }
                case '@': annotation(a, ref, api); return null;
                case '[': {
                    int n = a.readUnsignedShort();
                    for (int i = 0; i < n; i++) elementValue(a, ref, api);
                    return null;
                }
                default: a.readUnsignedShort(); return null;
            }
        }
    }

    /** instruction lengths (opcode + operands) for fixed-size instructions */
    static final int[] LEN = new int[256];
    static {
        Arrays.fill(LEN, 1);
        for (int op : new int[] {0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19, 0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9, 0xbc}) LEN[op] = 2;
        for (int op : new int[] {0x11, 0x13, 0x14, 0x84, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2,
                0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xbb, 0xbd, 0xc0, 0xc1,
                0xc6, 0xc7}) LEN[op] = 3;
        LEN[0xc5] = 4;
        LEN[0xb9] = 5;
        LEN[0xba] = 5;
        LEN[0xc8] = 5;
        LEN[0xc9] = 5;
    }

    // ----------------------------------------------------------- content

    static final Map<String, List<ClassInfo>> packages = new TreeMap<>();
    static final Map<String, String> packageVersion = new HashMap<>();
    static final Set<String> resourceDirs = new TreeSet<>();

    static void content(File f) throws IOException {
        if (f.isDirectory()) {
            Path root = f.toPath();
            try (java.util.stream.Stream<Path> st = Files.walk(root)) {
                for (Path p : (Iterable<Path>) st::iterator) {
                    if (Files.isDirectory(p)) continue;
                    String rel = root.relativize(p).toString().replace('\\', '/');
                    entry(rel, Files.readAllBytes(p));
                }
            }
        } else {
            try (ZipFile z = new ZipFile(f)) {
                for (ZipEntry e : Collections.list(z.entries())) {
                    if (e.isDirectory()) continue;
                    try (InputStream in = z.getInputStream(e)) { entry(e.getName(), in.readAllBytes()); }
                }
            }
        }
    }

    static void entry(String rel, byte[] data) throws IOException {
        if (rel.startsWith("META-INF/")) return;
        int s = rel.lastIndexOf('/');
        String pkg = s < 0 ? "" : rel.substring(0, s).replace('/', '.');
        if (rel.endsWith(".class")) {
            if (rel.endsWith("module-info.class")) return;
            ClassInfo ci = parse(data);
            packages.computeIfAbsent(ci.pkg, k -> new ArrayList<>()).add(ci);
            if (ci.version != null) packageVersion.put(ci.pkg, ci.version);
        } else {
            if (rel.endsWith("/packageinfo")) {
                for (String l : new String(data, StandardCharsets.UTF_8).split("\n")) {
                    l = l.trim();
                    if (l.startsWith("version ")) packageVersion.put(pkg, l.substring(8).trim());
                }
            }
            resourceDirs.add(pkg);
        }
    }

    // ------------------------------------------------------- instructions

    static final class Instr {
        Pattern p;
        boolean negate;
        String text;
        String name;
        LinkedHashMap<String, String> attrs = new LinkedHashMap<>();
        LinkedHashMap<String, String> dirs = new LinkedHashMap<>();
        boolean used;
    }

    static List<Instr> instructions(String header) {
        List<Instr> out = new ArrayList<>();
        if (header == null) return out;
        for (Osgi.Clause c : Osgi.parse(header)) {
            for (String n : c.names) {
                Instr i = new Instr();
                i.text = n;
                String pat = n;
                if (pat.startsWith("!")) { i.negate = true; pat = pat.substring(1); }
                i.name = pat;
                i.p = Pattern.compile(globRegex(pat));
                i.attrs.putAll(c.attrs);
                i.dirs.putAll(c.dirs);
                out.add(i);
            }
        }
        return out;
    }

    /** bnd package pattern: a.b (exact), a.b.* (a.b and below), * wildcards, {x|y} alternatives */
    static String globRegex(String pat) {
        if (pat.equals("*")) return ".*";
        String suffix = "";
        if (pat.endsWith(".*")) {
            pat = pat.substring(0, pat.length() - 2);
            suffix = "(\\..*)?";
        }
        StringBuilder r = new StringBuilder();
        for (char c : pat.toCharArray()) {
            switch (c) {
                case '{': r.append("(?:"); break;
                case '}': r.append(')'); break;
                case '|': r.append('|'); break;
                case '*': r.append(".*"); break;
                case '.': r.append("\\."); break;
                default: r.append(Pattern.quote(String.valueOf(c)));
            }
        }
        return r + suffix;
    }

    static Instr match(List<Instr> is, String pkg) {
        for (Instr i : is) {
            if (i.p.matcher(pkg).matches()) {
                i.used = true;
                return i.negate ? null : i;
            }
        }
        return null;
    }

    static String macros(String v, Map<String, String> vars) {
        Matcher m = Pattern.compile("\\$\\{([^}]+)\\}").matcher(v);
        StringBuffer b = new StringBuffer();
        while (m.find()) {
            String r = vars.get(m.group(1));
            m.appendReplacement(b, Matcher.quoteReplacement(r == null ? m.group(0) : macros(r, vars)));
        }
        m.appendTail(b);
        return b.toString();
    }

    // ----------------------------------------------------------- versions

    static int[] ver(String v) {
        String[] p = v.trim().split("\\.");
        int[] r = new int[3];
        for (int i = 0; i < 3 && i < p.length; i++) {
            try { r[i] = Integer.parseInt(p[i].replaceAll("[^0-9].*", "")); } catch (NumberFormatException e) { r[i] = 0; }
        }
        return r;
    }

    static String range(String v, boolean provider) {
        int[] x = ver(v);
        return provider ? "[" + x[0] + "." + x[1] + "," + x[0] + "." + (x[1] + 1) + ")"
                        : "[" + x[0] + "." + x[1] + "," + (x[0] + 1) + ")";
    }

    static String cleanVersion(String v) {
        int[] x = ver(v);
        String[] p = v.trim().split("\\.", 4);
        String s = x[0] + "." + x[1] + "." + x[2];
        if (p.length == 4) s += "." + p[3];
        return s;
    }

    // ---------------------------------------------------------------- main

    public static void main(String[] args) throws Exception {
        Map<String, String> vars = new HashMap<>();
        int i = 0;
        while (args[i].equals("-D")) {
            String d = args[i + 1];
            vars.put(d.substring(0, d.indexOf('=')), d.substring(d.indexOf('=') + 1));
            i += 2;
        }
        File content = new File(args[i]);
        Properties ins = new Properties() {
            final LinkedHashSet<Object> order = new LinkedHashSet<>();
            @Override public synchronized Object put(Object k, Object v) { order.add(k); return super.put(k, v); }
            @Override public Set<String> stringPropertyNames() { Set<String> s = new LinkedHashSet<>(); for (Object o : order) s.add((String) o); return s; }
        };
        try (Reader r = new InputStreamReader(new FileInputStream(args[i + 1]), StandardCharsets.UTF_8)) { ins.load(r); }
        File out = new File(args[i + 2]);
        String cp = args.length > i + 3 ? args[i + 3] : "";
        for (String k : ins.stringPropertyNames()) vars.putIfAbsent(k, ins.getProperty(k).trim());
        Map<String, String> h = new LinkedHashMap<>();
        for (String k : ins.stringPropertyNames()) h.put(k, macros(ins.getProperty(k).trim(), vars));

        content(content);

        // exporters on the class path: Export-Package, else package-info @Version
        Map<String, String> cpExports = new HashMap<>();
        List<File> cpFiles = new ArrayList<>();
        for (String e : cp.split(File.pathSeparator)) {
            if (e.isEmpty()) continue;
            File f = new File(e);
            if (!f.exists()) continue;
            cpFiles.add(f);
            Map<String, String> mf = Osgi.readManifest(f);
            if (mf != null) {
                for (Osgi.Clause c : Osgi.parse(Osgi.get(mf, "Export-Package"))) {
                    String v = c.attrs.getOrDefault("version", c.attrs.get("specification-version"));
                    for (String n : c.names) cpExports.putIfAbsent(n, v == null ? "" : v);
                }
            }
            if (f.isFile()) {
                try (ZipFile z = new ZipFile(f)) {
                    for (ZipEntry ze : Collections.list(z.entries())) {
                        String n = ze.getName();
                        if (!n.endsWith("/package-info.class") || n.startsWith("META-INF/")) continue;
                        try (InputStream in = z.getInputStream(ze)) {
                            ClassInfo pi = parse(in.readAllBytes());
                            if (pi.version != null) cpExports.putIfAbsent(pi.pkg, pi.version);
                        }
                    }
                }
            }
        }
        // packages with @ProviderType types that the bundle implements or extends
        Set<String> providerPkgs = new HashSet<>();
        Map<String, Boolean> ptCache = new HashMap<>();
        for (List<ClassInfo> l : packages.values()) {
            for (ClassInfo c : l) {
                for (String sup : c.supers) {
                    int sl = sup.lastIndexOf('/');
                    if (sl < 0) continue;
                    String sp = sup.substring(0, sl).replace('/', '.');
                    if (packages.containsKey(sp) || sp.startsWith("java.")) continue;
                    Boolean pt = ptCache.get(sup);
                    if (pt == null) {
                        pt = false;
                        for (File f : cpFiles) {
                            byte[] cb = classBytes(f, sup + ".class");
                            if (cb != null) { pt = parse(cb).providerType; break; }
                        }
                        ptCache.put(sup, pt);
                    }
                    if (pt) providerPkgs.add(sp);
                }
            }
        }

        // exports
        List<Instr> ex = instructions(h.containsKey("-exportcontents") ? h.get("-exportcontents") : h.get("Export-Package"));
        String defVersion = h.get("-exportversion");
        Set<String> all = new TreeSet<>(packages.keySet());
        all.addAll(resourceDirs);
        all.remove("");
        LinkedHashMap<String, Instr> exports = new LinkedHashMap<>();
        for (String p : all) {
            Instr m = match(ex, p);
            if (m != null) exports.put(p, m);
        }
        // imports
        Set<String> referenced = new TreeSet<>();
        for (List<ClassInfo> l : packages.values()) for (ClassInfo c : l) referenced.addAll(c.refs);
        List<Instr> im = instructions(h.getOrDefault("Import-Package", "*"));
        LinkedHashMap<String, String> imports = new LinkedHashMap<>();
        // exported packages are also imported (substitutable) when other
        // packages refer to them and they do not use private packages
        Set<String> privatePkgs = new HashSet<>(packages.keySet());
        privatePkgs.removeAll(exports.keySet());
        Set<String> referencedFromOthers = new HashSet<>();
        for (Map.Entry<String, List<ClassInfo>> e : packages.entrySet())
            for (ClassInfo c : e.getValue()) for (String r : c.refs) if (!r.equals(e.getKey())) referencedFromOthers.add(r);
        for (String p : referenced) {
            if (p.startsWith("java.") || p.equals("java")) continue;
            if (packages.containsKey(p) && !exports.containsKey(p)) continue;
            if (exports.containsKey(p)) {
                if (!referencedFromOthers.contains(p)) continue;
                boolean usesPrivate = false;
                for (ClassInfo c : packages.getOrDefault(p, Collections.emptyList()))
                    for (String r : c.refs) if (privatePkgs.contains(r)) usesPrivate = true;
                if (usesPrivate) continue;
            }
            Instr m = match(im, p);
            if (m == null) continue;
            StringBuilder s = new StringBuilder(p);
            String v = m.attrs.get("version");
            boolean provider = "true".equals(m.dirs.get("provide")) || providerPkgs.contains(p)
                    || exports.containsKey(p) && "true".equals(exports.get(p).dirs.get("provide"));
            if (v == null) {
                String ev = exports.containsKey(p) ? exportVersion(p, exports.get(p), defVersion) : cpExports.get(p);
                if (ev != null && !ev.isEmpty()) v = range(ev, provider);
            }
            for (Map.Entry<String, String> d : m.dirs.entrySet()) {
                if (d.getKey().equals("provide")) continue;
                s.append(';').append(d.getKey()).append(":=").append(d.getValue());
            }
            for (Map.Entry<String, String> a : m.attrs.entrySet()) {
                if (a.getKey().equals("version")) continue;
                s.append(';').append(a.getKey()).append("=\"").append(a.getValue()).append('"');
            }
            if (v != null && !v.isEmpty()) s.append(";version=\"").append(v).append('"');
            imports.put(p, s.toString());
        }
        // explicit imports of packages that are not referenced (bnd keeps
        // patterns without wildcards)
        for (Instr m : im) {
            if (m.negate || m.name.contains("*") || imports.containsKey(m.name)) continue;
            if (m.name.startsWith("java.")) continue;
            StringBuilder s = new StringBuilder(m.name);
            for (Map.Entry<String, String> d : m.dirs.entrySet()) s.append(';').append(d.getKey()).append(":=").append(d.getValue());
            for (Map.Entry<String, String> a : m.attrs.entrySet()) s.append(';').append(a.getKey()).append("=\"").append(a.getValue()).append('"');
            imports.put(m.name, s.toString());
        }

        // Export-Package with uses:
        List<String> exportClauses = new ArrayList<>();
        for (Map.Entry<String, Instr> e : exports.entrySet()) {
            String p = e.getKey();
            StringBuilder s = new StringBuilder(p);
            Set<String> uses = new TreeSet<>();
            for (ClassInfo c : packages.getOrDefault(p, Collections.emptyList())) {
                for (String r : c.api) {
                    if (r.startsWith("java.") || r.equals(p)) continue;
                    if (imports.containsKey(r) || exports.containsKey(r)) uses.add(r);
                }
            }
            Instr m = e.getValue();
            for (Map.Entry<String, String> d : m.dirs.entrySet()) {
                if (!d.getKey().equals("uses") && !d.getKey().equals("provide") && !d.getKey().startsWith("-"))
                    s.append(';').append(d.getKey()).append(":=\"").append(d.getValue()).append('"');
            }
            if (m.dirs.containsKey("uses")) uses = new TreeSet<>(Arrays.asList(m.dirs.get("uses").split("\\s*,\\s*")));
            if (!uses.isEmpty() && !"true".equals(h.get("-nouses"))) s.append(";uses:=\"").append(String.join(",", uses)).append('"');
            for (Map.Entry<String, String> a : m.attrs.entrySet()) {
                if (!a.getKey().equals("version")) s.append(';').append(a.getKey()).append("=\"").append(a.getValue()).append('"');
            }
            String v = exportVersion(p, m, defVersion);
            if (v != null) s.append(";version=\"").append(v).append('"');
            exportClauses.add(s.toString());
        }

        TreeMap<String, String> mf = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
        for (Map.Entry<String, String> e : h.entrySet()) {
            String k = e.getKey();
            if (k.startsWith("-") || k.equals("Export-Package") || k.equals("Import-Package") || k.equals("Private-Package")) continue;
            if (Character.isLowerCase(k.charAt(0))) continue; // macro definitions
            mf.put(k, e.getValue());
        }
        mf.put("Bundle-ManifestVersion", "2");
        if (mf.containsKey("Bundle-Version")) mf.put("Bundle-Version", cleanVersion(mf.get("Bundle-Version")));
        if (!exportClauses.isEmpty()) mf.put("Export-Package", String.join(",", exportClauses));
        if (!imports.isEmpty()) mf.put("Import-Package", String.join(",", imports.values()));
        if (!"true".equals(h.get("-noee"))) {
            int major = 0;
            for (List<ClassInfo> l : packages.values()) for (ClassInfo c : l) major = Math.max(major, c.major);
            if (major > 0) {
                String jv = major <= 52 ? "1." + (major - 44) : Integer.toString(major - 44);
                String ee = "osgi.ee;filter:=\"(&(osgi.ee=JavaSE)(version=" + jv + "))\"";
                String rc = mf.get("Require-Capability");
                mf.put("Require-Capability", rc == null ? ee : rc + "," + ee);
            }
        }
        String rm = h.get("-removeheaders");
        if (rm != null) for (String r : rm.split("\\s*,\\s*")) mf.remove(r);
        LinkedHashMap<String, String> ordered = new LinkedHashMap<>();
        ordered.put("Manifest-Version", "1.0");
        for (Map.Entry<String, String> e : mf.entrySet()) if (!e.getKey().equalsIgnoreCase("Manifest-Version")) ordered.put(e.getKey(), e.getValue());
        Osgi.writeManifest(ordered, out);
        for (Instr x : ex) if (!x.used && !x.name.contains("*")) System.err.println("jb.Bnd: warning: Export-Package " + x.text + " matches nothing");
    }

    static String exportVersion(String p, Instr m, String def) {
        String v = m.attrs.get("version");
        if (v == null) v = packageVersion.get(p);
        if (v == null) v = def;
        return v;
    }

    static byte[] classBytes(File f, String entry) throws IOException {
        if (f.isDirectory()) {
            File c = new File(f, entry);
            return c.isFile() ? Files.readAllBytes(c.toPath()) : null;
        }
        try (ZipFile z = new ZipFile(f)) {
            ZipEntry e = z.getEntry(entry);
            if (e == null) return null;
            try (InputStream in = z.getInputStream(e)) { return in.readAllBytes(); }
        }
    }
}
