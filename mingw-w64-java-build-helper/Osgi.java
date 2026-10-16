/*
 * OSGi bundle metadata for javabuild.sh's bundle mode (jb_bundle): what PDE
 * build / Tycho would read from MANIFEST.MF and build.properties.
 *
 *   java jb.Osgi header   MANIFEST|JAR NAME          value of a header (unwrapped)
 *   java jb.Osgi props    build.properties KEY        comma list of a key, one per line
 *   java jb.Osgi keys     build.properties PREFIX     keys starting with PREFIX
 *   java jb.Osgi manifest IN OUT [--qualifier Q] [--set 'Name: value']... [--remove NAME]...
 *        normalised manifest (qualifier replaced, 72-byte lines) for jar --manifest
 *   java jb.Osgi classpath --dirs D1;D2 [--nested DIR] [--extra BSN]... MANIFEST
 *        compile classpath of a bundle: the transitive closure of its
 *        Require-Bundle, Import-Package and Fragment-Host over the bundles
 *        (jars or directories) in the given directories, plus the fragments
 *        of the hosts in that closure that match win32/win32/x86_64
 *   java jb.Osgi order BUNDLE-DIR...
 *        the bundle directories sorted so that dependencies come first
 *   java jb.Osgi bundlesinfo --dirs D1;D2 [--start BSN@LEVEL]... [--all] OUT BSN...
 *        simpleconfigurator bundles.info for BSN... and everything they need
 *   java jb.Osgi bsnver JAR|DIR                          "bsn version"
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package jb;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import java.util.zip.*;

public class Osgi {

    // ---------------------------------------------------------------- manifest

    /** Header name (original case) -> unwrapped value, in file order. */
    static LinkedHashMap<String, String> readManifest(InputStream in) throws IOException {
        LinkedHashMap<String, String> m = new LinkedHashMap<>();
        BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        String line, name = null;
        StringBuilder val = null;
        boolean first = true;
        while ((line = r.readLine()) != null) {
            if (first && line.startsWith("﻿")) line = line.substring(1);
            first = false;
            if (line.startsWith(" ")) {
                if (val != null) val.append(line, 1, line.length());
                continue;
            }
            if (name != null) m.put(name, val.toString().trim());
            name = null;
            val = null;
            if (line.isEmpty()) {
                // main section ends at the first blank line
                if (!m.isEmpty()) break;
                continue;
            }
            int c = line.indexOf(':');
            if (c <= 0) continue;
            name = line.substring(0, c).trim();
            val = new StringBuilder(line.substring(c + 1).replaceFirst("^ ", ""));
        }
        if (name != null) m.put(name, val.toString().trim());
        return m;
    }

    static LinkedHashMap<String, String> readManifest(File f) throws IOException {
        if (f.isDirectory()) {
            File mf = new File(f, "META-INF/MANIFEST.MF");
            if (!mf.isFile()) return null;
            try (InputStream in = new FileInputStream(mf)) { return readManifest(in); }
        }
        if (f.getName().endsWith(".jar")) {
            try (ZipFile z = new ZipFile(f)) {
                ZipEntry e = z.getEntry("META-INF/MANIFEST.MF");
                if (e == null) return null;
                try (InputStream in = z.getInputStream(e)) { return readManifest(in); }
            }
        }
        try (InputStream in = new FileInputStream(f)) { return readManifest(in); }
    }

    static String get(Map<String, String> m, String name) {
        for (Map.Entry<String, String> e : m.entrySet()) {
            if (e.getKey().equalsIgnoreCase(name)) return e.getValue();
        }
        return null;
    }

    /** Writes a manifest with lines of at most 72 bytes, as java.util.jar does. */
    static void writeManifest(Map<String, String> m, File out) throws IOException {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        String mv = get(m, "Manifest-Version");
        writeHeader(b, "Manifest-Version", mv == null ? "1.0" : mv);
        for (Map.Entry<String, String> e : m.entrySet()) {
            if (e.getKey().equalsIgnoreCase("Manifest-Version")) continue;
            writeHeader(b, e.getKey(), e.getValue());
        }
        b.write("\r\n".getBytes(StandardCharsets.UTF_8));
        Files.write(out.toPath(), b.toByteArray());
    }

    static void writeHeader(OutputStream o, String name, String value) throws IOException {
        byte[] line = (name + ": " + value).getBytes(StandardCharsets.UTF_8);
        int pos = 0, max = 72;
        boolean first = true;
        while (pos < line.length) {
            int n = Math.min(first ? max : max - 1, line.length - pos);
            // do not split a UTF-8 sequence
            while (pos + n < line.length && (line[pos + n] & 0xC0) == 0x80) n--;
            if (!first) o.write(' ');
            o.write(line, pos, n);
            o.write('\r');
            o.write('\n');
            pos += n;
            first = false;
        }
        if (line.length == 0) o.write("\r\n".getBytes(StandardCharsets.UTF_8));
    }

    // ------------------------------------------------------------ header clauses

    static final class Clause {
        final List<String> names = new ArrayList<>();
        final LinkedHashMap<String, String> attrs = new LinkedHashMap<>();
        final LinkedHashMap<String, String> dirs = new LinkedHashMap<>();
    }

    /** Splits s at separator chars outside double quotes. */
    static List<String> split(String s, char sep) {
        List<String> out = new ArrayList<>();
        if (s == null) return out;
        StringBuilder cur = new StringBuilder();
        boolean q = false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"') q = !q;
            if (c == sep && !q) {
                out.add(cur.toString().trim());
                cur.setLength(0);
            } else {
                cur.append(c);
            }
        }
        if (cur.toString().trim().length() > 0) out.add(cur.toString().trim());
        return out;
    }

    static List<Clause> parse(String header) {
        List<Clause> out = new ArrayList<>();
        for (String cl : split(header, ',')) {
            if (cl.isEmpty()) continue;
            Clause c = new Clause();
            for (String p : split(cl, ';')) {
                int d = p.indexOf(":="), e = p.indexOf('=');
                if (d > 0 && (e < 0 || d < e)) {
                    c.dirs.put(p.substring(0, d).trim(), unquote(p.substring(d + 2).trim()));
                } else if (e > 0) {
                    String k = p.substring(0, e).trim();
                    int t = k.indexOf(':');
                    if (t > 0) k = k.substring(0, t);
                    c.attrs.put(k, unquote(p.substring(e + 1).trim()));
                } else {
                    c.names.add(p.trim());
                }
            }
            out.add(c);
        }
        return out;
    }

    static String unquote(String s) {
        if (s.length() >= 2 && s.startsWith("\"") && s.endsWith("\"")) return s.substring(1, s.length() - 1);
        return s;
    }

    // ------------------------------------------------------------- LDAP filter

    static final Map<String, String> PLATFORM = new HashMap<>();
    static {
        PLATFORM.put("osgi.os", "win32");
        PLATFORM.put("osgi.ws", "win32");
        PLATFORM.put("osgi.arch", "x86_64");
        PLATFORM.put("osgi.nl", "en_US");
    }

    /** Minimal RFC 1960 filter evaluation (=, presence, &, |, !) against PLATFORM. */
    static boolean filter(String f) {
        if (f == null || f.trim().isEmpty()) return true;
        int[] pos = {0};
        String s = f.replaceAll("\\s+(?=[()&|!])|(?<=[()&|!])\\s+", "");
        return eval(s, pos);
    }

    private static boolean eval(String s, int[] p) {
        if (s.charAt(p[0]) != '(') throw new IllegalArgumentException("bad filter " + s);
        p[0]++;
        char op = s.charAt(p[0]);
        boolean r;
        if (op == '&' || op == '|') {
            p[0]++;
            r = op == '&';
            while (s.charAt(p[0]) == '(') {
                boolean v = eval(s, p);
                r = op == '&' ? r && v : r || v;
            }
        } else if (op == '!') {
            p[0]++;
            r = !eval(s, p);
        } else {
            int end = s.indexOf(')', p[0]);
            String item = s.substring(p[0], end);
            p[0] = end;
            int eq = item.indexOf('=');
            String k = item.substring(0, eq).trim(), v = item.substring(eq + 1).trim();
            String have = PLATFORM.get(k);
            if (v.equals("*")) r = have != null;
            else r = have != null && have.equalsIgnoreCase(v);
        }
        if (s.charAt(p[0]) != ')') throw new IllegalArgumentException("bad filter " + s);
        p[0]++;
        return r;
    }

    // ------------------------------------------------------------- bundle index

    static final class Bundle {
        File file;
        String bsn, version;
        Map<String, String> mf;
        Set<String> exports = new LinkedHashSet<>();
        String host;
        boolean platformOk = true;
    }

    static String bsn(Map<String, String> mf) {
        String v = get(mf, "Bundle-SymbolicName");
        if (v == null) return null;
        List<Clause> c = parse(v);
        return c.isEmpty() || c.get(0).names.isEmpty() ? null : c.get(0).names.get(0);
    }

    static final List<Bundle> index = new ArrayList<>();
    static final Map<String, Bundle> byBsn = new HashMap<>();
    static final Map<String, List<Bundle>> byPkg = new HashMap<>();

    static void scan(String dirs) throws IOException {
        for (String d : dirs.split(java.util.regex.Pattern.quote(File.pathSeparator))) {
            if (d.isEmpty()) continue;
            File[] fs = new File(d).listFiles();
            if (fs == null) continue;
            Arrays.sort(fs);
            for (File f : fs) {
                if (!f.isDirectory() && !f.getName().endsWith(".jar")) continue;
                Map<String, String> mf = readManifest(f);
                if (mf == null) continue;
                String b = bsn(mf);
                if (b == null || byBsn.containsKey(b)) continue;
                add(f, mf, b);
            }
        }
    }

    static Bundle add(File f, Map<String, String> mf, String b) {
        Bundle x = new Bundle();
        x.file = f;
        x.bsn = b;
        x.mf = mf;
        x.version = get(mf, "Bundle-Version");
        for (Clause c : parse(get(mf, "Export-Package"))) x.exports.addAll(c.names);
        String h = get(mf, "Fragment-Host");
        if (h != null) x.host = parse(h).get(0).names.get(0);
        try {
            x.platformOk = filter(get(mf, "Eclipse-PlatformFilter"));
        } catch (RuntimeException e) {
            x.platformOk = true;
        }
        index.add(x);
        byBsn.put(b, x);
        for (String p : x.exports) byPkg.computeIfAbsent(p, k -> new ArrayList<>()).add(x);
        return x;
    }

    /** Direct dependencies (bundle symbolic names) of a manifest. */
    static Set<String> deps(Map<String, String> mf, String self, Set<String> selfExports, boolean warn) {
        Set<String> out = new LinkedHashSet<>();
        String h = get(mf, "Fragment-Host");
        if (h != null) out.add(parse(h).get(0).names.get(0));
        for (Clause c : parse(get(mf, "Require-Bundle"))) {
            for (String n : c.names) {
                if (byBsn.containsKey(n)) out.add(n);
                else if (warn && !"optional".equals(c.dirs.get("resolution")))
                    System.err.println("jb.Osgi: " + self + ": required bundle " + n + " not found");
            }
        }
        for (String hdr : new String[] {"Import-Package", "DynamicImport-Package"}) {
            for (Clause c : parse(get(mf, hdr))) {
                for (String n : c.names) {
                    if (selfExports.contains(n) || n.contains("*")) continue;
                    List<Bundle> prov = byPkg.get(n);
                    if (prov == null) {
                        if (warn && hdr.equals("Import-Package") && !"optional".equals(c.dirs.get("resolution"))
                                && !n.startsWith("java.") && !n.startsWith("javax.") && !n.startsWith("org.w3c.")
                                && !n.startsWith("org.xml.") && !n.startsWith("org.ietf.") && !n.startsWith("sun.")
                                && !n.startsWith("com.sun.") && !n.startsWith("jdk."))
                            System.err.println("jb.Osgi: " + self + ": imported package " + n + " not found");
                        continue;
                    }
                    out.add(prov.get(0).bsn);
                }
            }
        }
        out.remove(self);
        return out;
    }

    /** Transitive closure from a manifest, plus matching fragments of the hosts. */
    static List<Bundle> closure(Map<String, String> mf, List<String> extra) {
        String self = bsn(mf);
        Set<String> selfExports = new HashSet<>();
        for (Clause c : parse(get(mf, "Export-Package"))) selfExports.addAll(c.names);
        LinkedHashSet<String> seen = new LinkedHashSet<>();
        Deque<String> q = new ArrayDeque<>(deps(mf, self, selfExports, true));
        for (String e : extra) {
            if (byBsn.containsKey(e)) q.add(e);
            else System.err.println("jb.Osgi: extra bundle " + e + " not found");
        }
        boolean changed = true;
        while (changed) {
            while (!q.isEmpty()) {
                String b = q.poll();
                if (b.equals(self) || !seen.add(b)) continue;
                Bundle x = byBsn.get(b);
                q.addAll(deps(x.mf, x.bsn, x.exports, false));
            }
            changed = false;
            for (Bundle f : index) {
                if (f.host != null && f.platformOk && !seen.contains(f.bsn) && !f.bsn.equals(self)
                        && (seen.contains(f.host) || f.host.equals(self))) {
                    q.add(f.bsn);
                    changed = true;
                }
            }
        }
        List<Bundle> out = new ArrayList<>();
        for (String s : seen) out.add(byBsn.get(s));
        return out;
    }

    /** Class path entries of a bundle (itself and its Bundle-ClassPath jars). */
    static List<String> entries(Bundle b, File nested) throws IOException {
        List<String> out = new ArrayList<>();
        String bcp = get(b.mf, "Bundle-ClassPath");
        List<String> cp = new ArrayList<>();
        if (bcp == null) cp.add(".");
        else for (Clause c : parse(bcp)) cp.addAll(c.names);
        for (String e : cp) {
            if (e.equals(".") || e.equals("/")) {
                out.add(b.file.getPath());
            } else if (e.startsWith("external:")) {
                continue;
            } else if (b.file.isDirectory()) {
                File f = new File(b.file, e);
                if (f.exists()) out.add(f.getPath());
            } else if (nested != null) {
                try (ZipFile z = new ZipFile(b.file)) {
                    ZipEntry ze = z.getEntry(e);
                    if (ze == null || ze.isDirectory()) continue;
                    File dst = new File(nested, b.bsn + "_" + b.version + "/" + e);
                    if (!dst.isFile() || dst.lastModified() < b.file.lastModified()) {
                        dst.getParentFile().mkdirs();
                        try (InputStream in = z.getInputStream(ze)) {
                            Files.copy(in, dst.toPath(), StandardCopyOption.REPLACE_EXISTING);
                        }
                    }
                    out.add(dst.getPath());
                }
            }
        }
        return out;
    }

    // ------------------------------------------------------------------ props

    static Properties props(String file) throws IOException {
        Properties p = new Properties();
        try (InputStream in = new FileInputStream(file)) { p.load(in); }
        return p;
    }

    // ------------------------------------------------------------------ main

    public static void main(String[] a) throws Exception {
        String cmd = a[0];
        switch (cmd) {
            case "header": {
                Map<String, String> m = readManifest(new File(a[1]));
                String v = m == null ? null : get(m, a[2]);
                if (v != null) System.out.println(v);
                break;
            }
            case "bsnver": {
                Map<String, String> m = readManifest(new File(a[1]));
                System.out.println(bsn(m) + " " + get(m, "Bundle-Version"));
                break;
            }
            case "props": {
                String v = props(a[1]).getProperty(a[2]);
                if (v != null) for (String s : split(v, ',')) if (!s.isEmpty()) System.out.println(s);
                break;
            }
            case "keys": {
                Properties p = props(a[1]);
                TreeSet<String> ks = new TreeSet<>();
                for (String k : p.stringPropertyNames()) if (k.startsWith(a[2])) ks.add(k);
                for (String k : ks) System.out.println(k);
                break;
            }
            case "manifest": {
                LinkedHashMap<String, String> m = readManifest(new File(a[1]));
                String q = null;
                for (int i = 3; i < a.length; i++) {
                    switch (a[i]) {
                        case "--qualifier": q = a[++i]; break;
                        case "--set": {
                            String s = a[++i];
                            int c = s.indexOf(':');
                            String k = s.substring(0, c).trim(), v = s.substring(c + 1).trim();
                            String old = null;
                            for (String kk : m.keySet()) if (kk.equalsIgnoreCase(k)) old = kk;
                            if (old != null) m.put(old, v); else m.put(k, v);
                            break;
                        }
                        case "--remove": {
                            String k = a[++i];
                            m.keySet().removeIf(kk -> kk.equalsIgnoreCase(k));
                            break;
                        }
                        default: throw new IllegalArgumentException(a[i]);
                    }
                }
                if (q != null) {
                    for (Map.Entry<String, String> e : m.entrySet()) {
                        if (e.getKey().equalsIgnoreCase("Bundle-Version"))
                            e.setValue(e.getValue().replace("qualifier", q));
                    }
                }
                writeManifest(m, new File(a[2]));
                break;
            }
            case "classpath": {
                String dirs = "";
                File nested = null;
                List<String> extra = new ArrayList<>();
                List<String> optExtra = new ArrayList<>();
                String mfile = null;
                for (int i = 1; i < a.length; i++) {
                    switch (a[i]) {
                        case "--dirs": dirs = a[++i]; break;
                        case "--nested": nested = new File(a[++i]); break;
                        case "--extra": extra.add(a[++i]); break;
                        case "--extra-optional": {
                            String x = a[++i];
                            optExtra.add(x);
                            break;
                        }
                        default: mfile = a[i];
                    }
                }
                Map<String, String> mf = readManifest(new File(mfile));
                String self = bsn(mf);
                // never compile against an installed older copy of the bundle itself
                scanExcept(dirs, self);
                for (String x : optExtra) if (byBsn.containsKey(x)) extra.add(x);
                LinkedHashSet<String> cp = new LinkedHashSet<>();
                for (Bundle b : closure(mf, extra)) cp.addAll(entries(b, nested));
                System.out.println(String.join(File.pathSeparator, cp));
                break;
            }
            case "order": {
                // bundle source directories -> topological order
                Map<String, File> dirOf = new LinkedHashMap<>();
                for (int i = 1; i < a.length; i++) {
                    File d = new File(a[i]);
                    Map<String, String> mf = readManifest(d);
                    if (mf == null) throw new IOException("no META-INF/MANIFEST.MF in " + d);
                    String b = bsn(mf);
                    add(d, mf, b);
                    dirOf.put(b, d);
                }
                LinkedHashSet<String> done = new LinkedHashSet<>();
                for (String b : dirOf.keySet()) visit(b, dirOf, done, new HashSet<>());
                for (String b : done) System.out.println(a[0].equals("order") ? b + "\t" + dirOf.get(b).getPath() : b);
                break;
            }
            case "bundlesinfo": {
                String dirs = "";
                Map<String, String> start = new HashMap<>();
                List<String> roots = new ArrayList<>();
                String out = null;
                boolean all = false;
                for (int i = 1; i < a.length; i++) {
                    switch (a[i]) {
                        case "--dirs": dirs = a[++i]; break;
                        case "--start": {
                            String s = a[++i];
                            start.put(s.substring(0, s.indexOf('@')), s.substring(s.indexOf('@') + 1));
                            break;
                        }
                        case "--all": all = true; break;
                        default:
                            if (out == null) out = a[i]; else roots.add(a[i]);
                    }
                }
                scan(dirs);
                LinkedHashSet<String> sel = new LinkedHashSet<>();
                if (all) {
                    for (Bundle b : index) if (b.platformOk) sel.add(b.bsn);
                } else {
                    for (String r : roots) {
                        Bundle b = byBsn.get(r);
                        if (b == null) { System.err.println("jb.Osgi: no bundle " + r); System.exit(1); }
                        sel.add(r);
                        for (Bundle d : closure(b.mf, Collections.emptyList())) sel.add(d.bsn);
                    }
                    for (String s : start.keySet()) if (byBsn.containsKey(s)) {
                        sel.add(s);
                        for (Bundle d : closure(byBsn.get(s).mf, Collections.emptyList())) sel.add(d.bsn);
                    }
                }
                TreeSet<String> sorted = new TreeSet<>(sel);
                try (PrintWriter w = new PrintWriter(new OutputStreamWriter(new FileOutputStream(out), StandardCharsets.UTF_8))) {
                    w.print("#version=1\n");
                    for (String s : sorted) {
                        Bundle b = byBsn.get(s);
                        String st = start.getOrDefault(s, "4:false");
                        if (!st.contains(":")) st = st + ":true";
                        String loc = b.file.toURI().toString();
                        if (loc.endsWith("/")) loc = loc.substring(0, loc.length() - 1);
                        w.print(s + "," + b.version + "," + loc + "," + st.replace(':', ',') + "\n");
                    }
                }
                break;
            }
            default:
                throw new IllegalArgumentException("unknown command " + cmd);
        }
    }

    static void scanExcept(String dirs, String self) throws IOException {
        for (String d : dirs.split(java.util.regex.Pattern.quote(File.pathSeparator))) {
            if (d.isEmpty()) continue;
            File[] fs = new File(d).listFiles();
            if (fs == null) continue;
            Arrays.sort(fs);
            for (File f : fs) {
                if (!f.isDirectory() && !f.getName().endsWith(".jar")) continue;
                Map<String, String> mf = readManifest(f);
                if (mf == null) continue;
                String b = bsn(mf);
                if (b == null || b.equals(self) || byBsn.containsKey(b)) continue;
                add(f, mf, b);
            }
        }
    }

    static void visit(String b, Map<String, File> dirOf, LinkedHashSet<String> done, Set<String> stack) {
        if (done.contains(b) || !stack.add(b)) return;
        Bundle x = byBsn.get(b);
        for (String d : deps(x.mf, b, x.exports, false)) {
            if (dirOf.containsKey(d)) visit(d, dirOf, done, stack);
            // a dependency on a host is also one on its fragments (SWT's
            // classes live in the platform fragment)
            // (for a fragment's own host only the platform fragments, e.g.
            // org.eclipse.swt.svg after org.eclipse.swt.win32.win32.x86_64)
            boolean own = d.equals(x.host);
            for (Bundle f : index) {
                if (own && (get(f.mf, "Eclipse-PlatformFilter") == null || get(x.mf, "Eclipse-PlatformFilter") != null)) continue;
                if (d.equals(f.host) && f.platformOk && !f.bsn.equals(b) && dirOf.containsKey(f.bsn))
                    visit(f.bsn, dirOf, done, stack);
            }
        }
        done.add(b);
    }
}
