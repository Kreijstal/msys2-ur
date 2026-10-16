/*
 * Writes META-INF/plexus/components.xml from Plexus component metadata while
 * javac compiles a module, standing in for plexus-component-metadata (which
 * needs Maven to run; GNU Guix uses a shell script, components.sh, instead).
 *
 * Two kinds of metadata are understood:
 *  - org.codehaus.plexus.component.annotations.@Component / @Requirement /
 *    @Configuration (CLASS retention, also read from superclasses in jars)
 *  - the older javadoc tags  @plexus.component role="..." role-hint="..."
 *    and @plexus.requirement / @plexus.configuration on fields
 *
 * Like plexus-component-metadata, the static descriptors already in the
 * class output directory (META-INF/plexus/*.xml, copied there from
 * src/main/resources before compiling) are merged: their <component>
 * elements are kept in front of the generated ones.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package jb;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.*;
import javax.annotation.processing.*;
import javax.lang.model.SourceVersion;
import javax.lang.model.element.*;
import javax.lang.model.type.*;
import javax.tools.*;

public class PlexusComponentsProcessor extends AbstractProcessor {
    static final String ANN = "org.codehaus.plexus.component.annotations.";
    static final Pattern ATTR = Pattern.compile("([\\w.-]+)\\s*=\\s*\"([^\"]*)\"");

    private final StringBuilder out = new StringBuilder();
    private final Set<String> seen = new HashSet<>();
    private int count;

    @Override
    public Set<String> getSupportedAnnotationTypes() {
        return Collections.singleton("*");
    }

    @Override
    public SourceVersion getSupportedSourceVersion() {
        return SourceVersion.latestSupported();
    }

    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment env) {
        for (Element e : env.getRootElements()) {
            scan(e);
        }
        if (env.processingOver() && count > 0) {
            try {
                write();
            } catch (IOException ex) {
                processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR,
                        "components.xml: " + ex);
            }
        }
        return false;
    }

    void scan(Element e) {
        if (!(e instanceof TypeElement)) {
            return;
        }
        TypeElement t = (TypeElement) e;
        String name = processingEnv.getElementUtils().getBinaryName(t).toString();
        if (seen.add(name)) {
            component(t, name);
        }
        for (Element m : t.getEnclosedElements()) {
            scan(m);
        }
    }

    // -------------------------------------------------------------- helpers

    static AnnotationMirror find(Element e, String name) {
        for (AnnotationMirror m : e.getAnnotationMirrors()) {
            if (((TypeElement) m.getAnnotationType().asElement())
                    .getQualifiedName().contentEquals(name)) {
                return m;
            }
        }
        return null;
    }

    static Map<String, Object> values(AnnotationMirror m) {
        Map<String, Object> r = new HashMap<>();
        for (Map.Entry<? extends ExecutableElement, ? extends AnnotationValue> en
                : m.getElementValues().entrySet()) {
            r.put(en.getKey().getSimpleName().toString(), en.getValue().getValue());
        }
        return r;
    }

    String binaryName(TypeMirror t) {
        TypeMirror er = processingEnv.getTypeUtils().erasure(t);
        if (er.getKind() == TypeKind.DECLARED) {
            return processingEnv.getElementUtils()
                    .getBinaryName((TypeElement) ((DeclaredType) er).asElement()).toString();
        }
        if (er.getKind() == TypeKind.ARRAY) {
            return binaryName(((ArrayType) er).getComponentType()) + "[]";
        }
        return er.toString();
    }

    /** a javadoc tag's attributes (@plexus.component role="x" ...), or null */
    Map<String, String> tag(Element e, String tag) {
        String d = processingEnv.getElementUtils().getDocComment(e);
        if (d == null) {
            return null;
        }
        Matcher tm = Pattern.compile("@" + Pattern.quote(tag) + "(?![\\w.-])([^@]*)").matcher(d);
        if (!tm.find()) {
            return null;
        }
        Map<String, String> r = new LinkedHashMap<>();
        Matcher m = ATTR.matcher(tm.group(1));
        while (m.find()) {
            r.put(m.group(1), m.group(2));
        }
        return r;
    }

    String firstSentence(Element e) {
        String d = processingEnv.getElementUtils().getDocComment(e);
        if (d == null) {
            return null;
        }
        StringBuilder sb = new StringBuilder();
        for (String l : d.split("\n")) {
            l = l.trim();
            if (l.startsWith("@")) {
                break;
            }
            sb.append(l).append(' ');
        }
        String s = sb.toString().replaceAll("<[^>]+>", "").trim();
        int dot = s.indexOf(". ");
        if (dot >= 0) {
            s = s.substring(0, dot + 1);
        }
        return s.isEmpty() ? null : s;
    }

    static String esc(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    void el(int ind, String tag, String val) {
        if (val == null) {
            return;
        }
        for (int i = 0; i < ind; i++) {
            out.append("  ");
        }
        if (val.isEmpty()) {
            out.append('<').append(tag).append(" />\n");
        } else {
            out.append('<').append(tag).append('>').append(esc(val))
                    .append("</").append(tag).append(">\n");
        }
    }

    // ------------------------------------------------------------ component

    void component(TypeElement t, String impl) {
        String role, hint, strategy, description, isolated;
        AnnotationMirror cm = find(t, ANN + "Component");
        Map<String, String> jt = cm == null ? tag(t, "plexus.component") : null;
        if (cm != null) {
            Map<String, Object> v = values(cm);
            role = binaryName((TypeMirror) v.get("role"));
            hint = (String) v.getOrDefault("hint", "");
            strategy = (String) v.getOrDefault("instantiationStrategy", "");
            description = (String) v.getOrDefault("description", "");
            isolated = String.valueOf(v.getOrDefault("isolatedRealm", false));
        } else if (jt != null) {
            role = jt.get("role");
            hint = jt.getOrDefault("role-hint", "");
            strategy = jt.getOrDefault("instantiation-strategy", "");
            description = jt.getOrDefault("description", firstSentence(t));
            isolated = jt.getOrDefault("isolated-realm", "false");
            if (role == null) {
                processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR,
                        "@plexus.component without role", t);
                return;
            }
        } else {
            return;
        }
        count++;
        out.append("    <component>\n");
        el(3, "role", role);
        el(3, "role-hint", hint.isEmpty() ? "default" : hint);
        el(3, "implementation", impl);
        if (!strategy.isEmpty()) {
            el(3, "instantiation-strategy", strategy);
        }
        el(3, "description", description == null ? "" : description);
        el(3, "isolated-realm", isolated);
        StringBuilder reqs = new StringBuilder();
        StringBuilder conf = new StringBuilder();
        fields(t, reqs, conf, new HashSet<>());
        if (reqs.length() > 0) {
            out.append("      <requirements>\n").append(reqs).append("      </requirements>\n");
        }
        if (conf.length() > 0) {
            out.append("      <configuration>\n").append(conf).append("      </configuration>\n");
        }
        out.append("    </component>\n");
    }

    void fields(TypeElement t, StringBuilder reqs, StringBuilder conf, Set<String> names) {
        for (Element e : t.getEnclosedElements()) {
            if (e.getKind() != ElementKind.FIELD) {
                continue;
            }
            // like plexus-component-metadata, a superclass field hidden by a
            // field of the same name is still listed
            String field = e.getSimpleName().toString();
            AnnotationMirror rm = find(e, ANN + "Requirement");
            Map<String, String> rt = rm == null ? tag(e, "plexus.requirement") : null;
            if (rm != null || rt != null) {
                String role = null, hint = "", optional = null;
                List<String> hints = new ArrayList<>();
                if (rm != null) {
                    Map<String, Object> v = values(rm);
                    if (v.containsKey("role")) {
                        role = binaryName((TypeMirror) v.get("role"));
                    }
                    hint = (String) v.getOrDefault("hint", "");
                    Object hs = v.get("hints");
                    if (hs instanceof List) {
                        for (Object h : (List<?>) hs) {
                            hints.add(String.valueOf(((AnnotationValue) h).getValue()));
                        }
                    }
                    if (Boolean.TRUE.equals(v.get("optional"))) {
                        optional = "true";
                    }
                } else {
                    role = rt.get("role");
                    hint = rt.getOrDefault("role-hint", "");
                    optional = rt.get("optional");
                }
                if (role == null || role.equals("java.lang.Object")) {
                    // the raw field type, also for List/Map requirements
                    // (Sisu takes the element type from the field)
                    role = binaryName(e.asType());
                }
                reqs.append("        <requirement>\n");
                ind(reqs, 5).append("<role>").append(esc(role)).append("</role>\n");
                if (!hint.isEmpty()) {
                    ind(reqs, 5).append("<role-hint>").append(esc(hint)).append("</role-hint>\n");
                }
                if (!hints.isEmpty()) {
                    ind(reqs, 5).append("<role-hints>\n");
                    for (String h : hints) {
                        ind(reqs, 6).append("<role-hint>").append(esc(h)).append("</role-hint>\n");
                    }
                    ind(reqs, 5).append("</role-hints>\n");
                }
                ind(reqs, 5).append("<field-name>").append(field).append("</field-name>\n");
                if (optional != null) {
                    ind(reqs, 5).append("<optional>").append(optional).append("</optional>\n");
                }
                reqs.append("        </requirement>\n");
            }
            AnnotationMirror cm = find(e, ANN + "Configuration");
            Map<String, String> ct = cm == null ? tag(e, "plexus.configuration") : null;
            if (cm != null || ct != null) {
                String name, value;
                if (cm != null) {
                    Map<String, Object> v = values(cm);
                    name = (String) v.getOrDefault("name", "");
                    value = String.valueOf(v.get("value"));
                } else {
                    name = ct.getOrDefault("name", "");
                    value = ct.getOrDefault("default-value", "");
                }
                if (name.isEmpty()) {
                    name = field.replaceAll("([a-z])([A-Z])", "$1-$2").toLowerCase(Locale.ROOT);
                }
                ind(conf, 4).append('<').append(name).append('>').append(esc(value))
                        .append("</").append(name).append(">\n");
            }
        }
        TypeMirror sup = t.getSuperclass();
        if (sup.getKind() == TypeKind.DECLARED) {
            fields((TypeElement) ((DeclaredType) sup).asElement(), reqs, conf, names);
        }
    }

    static StringBuilder ind(StringBuilder sb, int n) {
        for (int i = 0; i < n; i++) {
            sb.append("  ");
        }
        return sb;
    }

    /** the <components> content of a descriptor */
    static String components(CharSequence xml) {
        Matcher m = Pattern.compile("(?s)<components>(.*)</components>").matcher(xml);
        return m.find() ? m.group(1).replaceAll("^\\s*\\n", "").replaceAll("\\s+$", "") : "";
    }

    void write() throws IOException {
        Filer filer = processingEnv.getFiler();
        // like plexus-component-metadata, merge the static descriptors that
        // were copied from src/main/resources/META-INF/plexus (components.xml
        // first, then the other *.xml files by name)
        StringBuilder existing = new StringBuilder();
        try {
            FileObject probe = filer.getResource(StandardLocation.CLASS_OUTPUT, "",
                    "META-INF/plexus/components.xml");
            java.nio.file.Path dir = java.nio.file.Paths.get(probe.toUri()).getParent();
            if (java.nio.file.Files.isDirectory(dir)) {
                List<java.nio.file.Path> files = new ArrayList<>();
                try (java.util.stream.Stream<java.nio.file.Path> st = java.nio.file.Files.list(dir)) {
                    st.filter(f -> f.getFileName().toString().endsWith(".xml")).forEach(files::add);
                }
                files.sort(Comparator.comparing((java.nio.file.Path f) ->
                        !f.getFileName().toString().equals("components.xml"))
                        .thenComparing(f -> f.getFileName().toString()));
                for (java.nio.file.Path f : files) {
                    String c = components(new String(java.nio.file.Files.readAllBytes(f),
                            StandardCharsets.UTF_8));
                    if (!c.trim().isEmpty()) {
                        existing.append(c).append('\n');
                    }
                }
            }
        } catch (IOException | IllegalArgumentException | UnsupportedOperationException missing) {
            // nothing to merge
        }
        FileObject fo = filer.createResource(StandardLocation.CLASS_OUTPUT, "",
                "META-INF/plexus/components.xml");
        try (Writer w = new OutputStreamWriter(fo.openOutputStream(), StandardCharsets.UTF_8)) {
            w.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<component-set>\n  <components>\n");
            w.write(existing.toString());
            w.write(out.toString());
            w.write("  </components>\n</component-set>\n");
        }
    }
}
