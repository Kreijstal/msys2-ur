/*
 * Writes META-INF/maven/plugin.xml for a Maven plugin from its
 * org.apache.maven.plugins.annotations (@Mojo, @Parameter, @Component,
 * @Execute) while javac compiles it.  This stands in for maven-plugin-plugin
 * (maven-plugin-tools), which cannot run before Maven exists; GNU Guix does
 * the same job in guix/build/maven/plugin.scm.
 *
 * The annotations have CLASS retention, so they are read from the language
 * model: javac also exposes them for superclasses that come from jars (for
 * example AbstractSurefireMojo in maven-surefire-common).
 *
 * Option -Ajb.plugin=<file> names a java.util.Properties file with groupId,
 * artifactId, version, goalPrefix, name, description, requiredJavaVersion,
 * requiredMavenVersion and dependency.N=groupId:artifactId:type:version.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package jb;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import javax.annotation.processing.*;
import javax.lang.model.SourceVersion;
import javax.lang.model.element.*;
import javax.lang.model.type.*;
import javax.lang.model.util.*;
import javax.tools.*;

@SupportedOptions("jb.plugin")
public class MojoDescriptorProcessor extends AbstractProcessor {
    static final String ANN = "org.apache.maven.plugins.annotations.";

    private final Map<String, TypeElement> mojos = new TreeMap<>();

    @Override
    public Set<String> getSupportedAnnotationTypes() {
        return Collections.singleton(ANN + "Mojo");
    }

    @Override
    public SourceVersion getSupportedSourceVersion() {
        return SourceVersion.latestSupported();
    }

    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment env) {
        for (TypeElement a : annotations) {
            for (Element e : env.getElementsAnnotatedWith(a)) {
                if (e instanceof TypeElement) {
                    TypeElement t = (TypeElement) e;
                    mojos.put(t.getQualifiedName().toString(), t);
                }
            }
        }
        if (env.processingOver() && !mojos.isEmpty()) {
            try {
                write();
            } catch (IOException ex) {
                processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR,
                        "plugin.xml: " + ex);
            }
        }
        return false;
    }

    // ---------------------------------------------------------------- model

    static AnnotationMirror find(Element e, String name) {
        for (AnnotationMirror m : e.getAnnotationMirrors()) {
            if (((TypeElement) m.getAnnotationType().asElement())
                    .getQualifiedName().contentEquals(name)) {
                return m;
            }
        }
        return null;
    }

    /** explicitly given annotation values, by name */
    static Map<String, Object> values(AnnotationMirror m) {
        Map<String, Object> r = new HashMap<>();
        if (m == null) {
            return r;
        }
        for (Map.Entry<? extends ExecutableElement, ? extends AnnotationValue> en
                : m.getElementValues().entrySet()) {
            r.put(en.getKey().getSimpleName().toString(), en.getValue().getValue());
        }
        return r;
    }

    static String str(Map<String, Object> v, String k, String def) {
        Object o = v.get(k);
        if (o == null) {
            return def;
        }
        if (o instanceof VariableElement) {          // enum constant
            return ((VariableElement) o).getSimpleName().toString();
        }
        return o.toString();
    }

    static boolean bool(Map<String, Object> v, String k, boolean def) {
        Object o = v.get(k);
        return o == null ? def : (Boolean) o;
    }

    /** LifecyclePhase / ResolutionScope / InstantiationStrategy constant -> id */
    static String enumId(String constant) {
        switch (constant) {
            case "COMPILE_PLUS_RUNTIME": return "compile+runtime";
            case "RUNTIME_PLUS_SYSTEM": return "runtime+system";
            default: return constant.toLowerCase(Locale.ROOT).replace('_', '-');
        }
    }

    String binaryName(TypeMirror t) {
        Types types = processingEnv.getTypeUtils();
        TypeMirror er = types.erasure(t);
        switch (er.getKind()) {
            case ARRAY:
                return binaryName(((ArrayType) er).getComponentType()) + "[]";
            case DECLARED:
                return processingEnv.getElementUtils()
                        .getBinaryName((TypeElement) ((DeclaredType) er).asElement()).toString();
            default:
                return er.toString();
        }
    }

    /** the type as maven-plugin-tools prints it: generic arguments kept */
    String genericName(TypeMirror t) {
        if (t.getKind() == TypeKind.DECLARED) {
            DeclaredType d = (DeclaredType) t;
            StringBuilder sb = new StringBuilder(binaryName(t));
            if (!d.getTypeArguments().isEmpty()) {
                sb.append('<');
                boolean first = true;
                for (TypeMirror a : d.getTypeArguments()) {
                    if (!first) {
                        sb.append(',');
                    }
                    first = false;
                    sb.append(a.getKind() == TypeKind.DECLARED || a.getKind() == TypeKind.ARRAY
                            ? genericName(a) : a.toString());
                }
                sb.append('>');
            }
            return sb.toString();
        }
        if (t.getKind() == TypeKind.ARRAY) {
            return genericName(((ArrayType) t).getComponentType()) + "[]";
        }
        return binaryName(t);
    }

    String doc(Element e) {
        String d = processingEnv.getElementUtils().getDocComment(e);
        if (d == null) {
            return null;
        }
        StringBuilder sb = new StringBuilder();
        for (String line : d.split("\n")) {
            String l = line.trim();
            if (l.startsWith("@")) {
                break;                                  // block tags
            }
            sb.append(l).append('\n');
        }
        String s = sb.toString().trim()
                .replaceAll("\\{@(?:link|linkplain|code|literal) +([^}]*)}", "$1")
                .replaceAll("<[^>]+>", "");
        return s.isEmpty() ? null : s;
    }

    static final class Param {
        String name, alias, type, generic, property, defaultValue, description, since;
        boolean required, editable = true, deprecated;
        String deprecatedText;
    }

    static final class Req {
        String role, hint, field;
    }

    /** parameters and requirements of a mojo class, superclasses first */
    void collect(TypeElement t, Map<String, Param> params, Map<String, Req> reqs) {
        TypeMirror sup = t.getSuperclass();
        if (sup.getKind() == TypeKind.DECLARED) {
            collect((TypeElement) ((DeclaredType) sup).asElement(), params, reqs);
        }
        for (Element e : t.getEnclosedElements()) {
            TypeMirror type;
            String name;
            if (e.getKind() == ElementKind.FIELD) {
                type = e.asType();
                name = e.getSimpleName().toString();
            } else if (e.getKind() == ElementKind.METHOD
                    && ((ExecutableElement) e).getParameters().size() == 1
                    && e.getSimpleName().toString().startsWith("set")
                    && e.getSimpleName().length() > 3) {
                type = ((ExecutableElement) e).getParameters().get(0).asType();
                String s = e.getSimpleName().toString().substring(3);
                name = Character.toLowerCase(s.charAt(0)) + s.substring(1);
            } else {
                continue;
            }
            AnnotationMirror pm = find(e, ANN + "Parameter");
            AnnotationMirror cm = find(e, ANN + "Component");
            if (pm != null) {
                Map<String, Object> v = values(pm);
                Param p = new Param();
                p.name = str(v, "name", "").isEmpty() ? name : str(v, "name", "");
                p.alias = emptyNull(str(v, "alias", null));
                p.property = emptyNull(str(v, "property", null));
                // an explicit defaultValue = "" is kept, as maven-plugin-tools does
                p.defaultValue = str(v, "defaultValue", null);
                p.required = bool(v, "required", false);
                p.editable = !bool(v, "readonly", false);
                p.type = binaryName(type);
                p.generic = genericName(type);
                p.description = doc(e);
                p.deprecated = find(e, "java.lang.Deprecated") != null;
                params.remove(p.name);
                params.put(p.name, p);
            } else if (cm != null) {
                Map<String, Object> v = values(cm);
                String role = v.containsKey("role")
                        ? binaryName((TypeMirror) v.get("role")) : binaryName(type);
                String expr = expression(role);
                if (expr != null) {
                    // MavenSession, MavenProject, ... are read-only parameters
                    Param p = new Param();
                    p.name = name;
                    p.type = binaryName(type);
                    p.generic = genericName(type);
                    p.defaultValue = expr;
                    p.editable = false;
                    p.description = doc(e);
                    params.remove(p.name);
                    params.put(p.name, p);
                } else {
                    Req r = new Req();
                    r.role = role;
                    r.hint = emptyNull(str(v, "hint", null));
                    r.field = name;
                    reqs.put(name, r);
                }
            }
        }
    }

    static String expression(String role) {
        switch (role) {
            case "org.apache.maven.execution.MavenSession": return "${session}";
            case "org.apache.maven.project.MavenProject": return "${project}";
            case "org.apache.maven.plugin.MojoExecution": return "${mojoExecution}";
            case "org.apache.maven.plugin.descriptor.PluginDescriptor": return "${plugin}";
            case "org.apache.maven.settings.Settings": return "${settings}";
            default: return null;
        }
    }

    static String emptyNull(String s) {
        return s == null || s.isEmpty() ? null : s;
    }

    // --------------------------------------------------------------- output

    static String esc(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\"", "&quot;");
    }

    static void el(PrintWriter w, int ind, String tag, Object val) {
        if (val == null) {
            return;
        }
        w.print(pad(ind));
        w.println("<" + tag + ">" + esc(val.toString()) + "</" + tag + ">");
    }

    static String pad(int n) {
        char[] c = new char[n * 2];
        Arrays.fill(c, ' ');
        return new String(c);
    }

    void write() throws IOException {
        Properties pp = new Properties();
        String f = processingEnv.getOptions().get("jb.plugin");
        if (f == null) {
            throw new IOException("option -Ajb.plugin=<properties> is required");
        }
        try (Reader r = new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8)) {
            pp.load(r);
        }
        FileObject fo = processingEnv.getFiler().createResource(StandardLocation.CLASS_OUTPUT,
                "", "META-INF/maven/plugin.xml");
        try (PrintWriter w = new PrintWriter(new OutputStreamWriter(fo.openOutputStream(),
                StandardCharsets.UTF_8))) {
            w.println("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
            w.println();
            w.println("<!-- Generated by javabuild MojoDescriptorProcessor -->");
            w.println();
            w.println("<plugin>");
            el(w, 1, "name", pp.getProperty("name", pp.getProperty("artifactId")));
            el(w, 1, "description", pp.getProperty("description"));
            el(w, 1, "groupId", pp.getProperty("groupId"));
            el(w, 1, "artifactId", pp.getProperty("artifactId"));
            el(w, 1, "version", pp.getProperty("version"));
            el(w, 1, "goalPrefix", pp.getProperty("goalPrefix"));
            el(w, 1, "isolatedRealm", "false");
            el(w, 1, "inheritedByDefault", "true");
            el(w, 1, "requiredJavaVersion", pp.getProperty("requiredJavaVersion"));
            el(w, 1, "requiredMavenVersion", pp.getProperty("requiredMavenVersion"));
            w.println("  <mojos>");
            List<String[]> goals = new ArrayList<>();
            for (TypeElement t : mojos.values()) {
                goals.add(new String[] {str(values(find(t, ANN + "Mojo")), "name", ""),
                        t.getQualifiedName().toString()});
            }
            goals.sort(Comparator.comparing(g -> g[0]));
            for (String[] g : goals) {
                mojo(w, mojos.get(g[1]));
            }
            w.println("  </mojos>");
            w.println("  <dependencies>");
            for (int i = 0; pp.containsKey("dependency." + i); i++) {
                String[] d = pp.getProperty("dependency." + i).split(":");
                w.println("    <dependency>");
                el(w, 3, "groupId", d[0]);
                el(w, 3, "artifactId", d[1]);
                el(w, 3, "type", d[2]);
                el(w, 3, "version", d[3]);
                w.println("    </dependency>");
            }
            w.println("  </dependencies>");
            w.println("</plugin>");
        }
    }

    void mojo(PrintWriter w, TypeElement t) {
        Map<String, Object> v = values(find(t, ANN + "Mojo"));
        Map<String, Object> ex = values(find(t, ANN + "Execute"));
        w.println("    <mojo>");
        el(w, 3, "goal", str(v, "name", null));
        el(w, 3, "description", doc(t));
        String res = enumId(str(v, "requiresDependencyResolution", "NONE"));
        if (!res.equals("none")) {
            el(w, 3, "requiresDependencyResolution", res);
        }
        String col = enumId(str(v, "requiresDependencyCollection", "NONE"));
        if (!col.equals("none")) {
            el(w, 3, "requiresDependencyCollection", col);
        }
        el(w, 3, "requiresDirectInvocation", bool(v, "requiresDirectInvocation", false));
        el(w, 3, "requiresProject", bool(v, "requiresProject", true));
        el(w, 3, "requiresReports", bool(v, "requiresReports", false));
        el(w, 3, "aggregator", bool(v, "aggregator", false));
        el(w, 3, "requiresOnline", bool(v, "requiresOnline", false));
        el(w, 3, "inheritedByDefault", bool(v, "inheritByDefault", true));
        String phase = enumId(str(v, "defaultPhase", "NONE"));
        if (!phase.equals("none")) {
            el(w, 3, "phase", phase);
        }
        if (!ex.isEmpty()) {
            String ep = enumId(str(ex, "phase", "NONE"));
            if (!ep.equals("none")) {
                el(w, 3, "executePhase", ep);
            }
            el(w, 3, "executeGoal", emptyNull(str(ex, "goal", null)));
            el(w, 3, "executeLifecycle", emptyNull(str(ex, "lifecycle", null)));
        }
        el(w, 3, "implementation", processingEnv.getElementUtils().getBinaryName(t));
        el(w, 3, "language", "java");
        el(w, 3, "configurator", emptyNull(str(v, "configurator", null)));
        el(w, 3, "instantiationStrategy", enumId(str(v, "instantiationStrategy", "PER_LOOKUP")));
        el(w, 3, "executionStrategy", str(v, "executionStrategy", "once-per-session"));
        el(w, 3, "threadSafe", bool(v, "threadSafe", false));
        Map<String, Param> params = new LinkedHashMap<>();
        Map<String, Req> reqs = new TreeMap<>();
        collect(t, params, reqs);
        List<Param> ps = new ArrayList<>(params.values());
        ps.sort(Comparator.comparing(p -> p.name));
        w.println("      <parameters>");
        for (Param p : ps) {
            w.println("        <parameter>");
            el(w, 5, "name", p.name);
            el(w, 5, "alias", p.alias);
            el(w, 5, "type", p.type);
            el(w, 5, "required", p.required);
            el(w, 5, "editable", p.editable);
            el(w, 5, "description", p.description == null ? "" : p.description);
            w.println("        </parameter>");
        }
        w.println("      </parameters>");
        w.println("      <configuration>");
        for (Param p : ps) {
            // like maven-plugin-tools: no element for an empty default
            // without property; default-value="" is kept next to a property
            if (p.property == null && (p.defaultValue == null || p.defaultValue.isEmpty())) {
                continue;
            }
            StringBuilder sb = new StringBuilder(pad(4)).append('<').append(p.name)
                    .append(" implementation=\"").append(esc(p.type)).append('"');
            if (p.defaultValue != null) {
                sb.append(" default-value=\"").append(esc(p.defaultValue)).append('"');
            }
            if (p.property != null) {
                sb.append('>').append(esc("${" + p.property + "}"))
                        .append("</").append(p.name).append('>');
            } else {
                sb.append("/>");
            }
            w.println(sb);
        }
        w.println("      </configuration>");
        if (!reqs.isEmpty()) {
            w.println("      <requirements>");
            for (Req r : reqs.values()) {
                w.println("        <requirement>");
                el(w, 5, "role", r.role);
                el(w, 5, "role-hint", r.hint);
                el(w, 5, "field-name", r.field);
                w.println("        </requirement>");
            }
            w.println("      </requirements>");
        }
        w.println("    </mojo>");
    }
}
