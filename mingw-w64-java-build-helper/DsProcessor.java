/*
 * Annotation processor that writes OSGi Declarative Services component
 * descriptions (OSGI-INF/<component name>.xml) from the standard
 * org.osgi.service.component.annotations, as bnd does for PDE/Tycho builds
 * (.settings/org.eclipse.pde.ds.annotations.prefs).  The XML follows bnd's
 * layout: attributes in bnd's order, references sorted by name, properties
 * before the service element, and the lowest namespace that covers the
 * features used (at least 1.3, the annotations' own version).
 *
 * options:  -Ajb.ds.path=OSGI-INF   output folder inside the class output
 *           -Ajb.ds.list=FILE       also write the generated paths to FILE
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

@SupportedAnnotationTypes("org.osgi.service.component.annotations.Component")
@SupportedOptions({"jb.ds.path", "jb.ds.list"})
public class DsProcessor extends AbstractProcessor {
    static final String P = "org.osgi.service.component.annotations.";
    final List<String> written = new ArrayList<>();

    @Override
    public SourceVersion getSupportedSourceVersion() {
        return SourceVersion.latestSupported();
    }

    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment env) {
        if (env.processingOver()) {
            String list = processingEnv.getOptions().get("jb.ds.list");
            if (list != null) {
                try (Writer w = new OutputStreamWriter(new FileOutputStream(list, true), StandardCharsets.UTF_8)) {
                    for (String s : written) w.write(s + "\n");
                } catch (IOException e) {
                    error(null, "cannot write " + list + ": " + e);
                }
            }
            return false;
        }
        TypeElement comp = processingEnv.getElementUtils().getTypeElement(P + "Component");
        if (comp == null) return false;
        for (Element e : env.getElementsAnnotatedWith(comp)) {
            if (e.getKind() == ElementKind.CLASS) {
                try {
                    component((TypeElement) e);
                } catch (RuntimeException ex) {
                    error(e, "DS: " + ex);
                }
            }
        }
        return false;
    }

    void error(Element e, String msg) {
        processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR, msg, e);
    }

    // ------------------------------------------------------------ annotations

    static AnnotationMirror find(Element e, String type) {
        for (AnnotationMirror m : e.getAnnotationMirrors()) {
            if (name(m).equals(type)) return m;
        }
        return null;
    }

    static String name(AnnotationMirror m) {
        return ((TypeElement) m.getAnnotationType().asElement()).getQualifiedName().toString();
    }

    /** explicitly given element value or null */
    static Object val(AnnotationMirror m, String el) {
        if (m == null) return null;
        for (Map.Entry<? extends ExecutableElement, ? extends AnnotationValue> e : m.getElementValues().entrySet()) {
            if (e.getKey().getSimpleName().contentEquals(el)) return e.getValue().getValue();
        }
        return null;
    }

    String str(AnnotationMirror m, String el) {
        Object v = val(m, el);
        return v == null ? null : v.toString();
    }

    /** enum constant name of an element, or null */
    String enm(AnnotationMirror m, String el) {
        Object v = val(m, el);
        return v instanceof VariableElement ? ((VariableElement) v).getSimpleName().toString() : null;
    }

    @SuppressWarnings("unchecked")
    static List<AnnotationValue> list(AnnotationMirror m, String el) {
        Object v = val(m, el);
        if (v == null) return null;
        if (v instanceof List) return (List<AnnotationValue>) v;
        return null;
    }

    String binary(TypeMirror t) {
        t = processingEnv.getTypeUtils().erasure(t);
        if (t.getKind() == TypeKind.DECLARED) {
            return processingEnv.getElementUtils()
                    .getBinaryName((TypeElement) ((DeclaredType) t).asElement()).toString();
        }
        return t.toString();
    }

    // -------------------------------------------------------------- model

    static final class Ref implements Comparable<Ref> {
        String name, cardinality, policy, iface, target, bind, unbind, updated, policyOption, scope,
                field, fieldOption, fieldCollectionType, parameter;

        public int compareTo(Ref o) {
            return name.compareTo(o.name);
        }
    }

    static final class Prop {
        String name, type = "String";
        List<String> values = new ArrayList<>();
        boolean multi;
    }

    // DS namespace versions as integers: 1.3 -> 13
    int version;

    void need(int v) {
        if (v > version) version = v;
    }

    void component(TypeElement t) throws RuntimeException {
        version = 13;
        AnnotationMirror c = find(t, P + "Component");
        String cname = str(c, "name");
        if (cname == null) cname = processingEnv.getElementUtils().getBinaryName(t).toString();

        // properties: component property types on the class, then property=
        LinkedHashMap<String, Prop> props = new LinkedHashMap<>();
        for (AnnotationMirror m : t.getAnnotationMirrors()) {
            if (isPropertyType(m)) propertyType(m, props, false);
        }

        // services
        List<String> services = new ArrayList<>();
        List<AnnotationValue> sv = list(c, "service");
        if (sv != null) {
            for (AnnotationValue v : sv) services.add(binary((TypeMirror) v.getValue()));
        } else {
            for (TypeMirror i : t.getInterfaces()) services.add(binary(i));
        }

        String activate = null, deactivate = null, modified = null, init = null;
        List<Ref> refs = new ArrayList<>();
        for (Element e : t.getEnclosedElements()) {
            if (e.getKind() == ElementKind.METHOD) {
                ExecutableElement m = (ExecutableElement) e;
                if (find(m, P + "Activate") != null) {
                    activate = m.getSimpleName().toString();
                    lifecycleParams(m, props);
                }
                if (find(m, P + "Deactivate") != null) deactivate = m.getSimpleName().toString();
                if (find(m, P + "Modified") != null) {
                    modified = m.getSimpleName().toString();
                    lifecycleParams(m, props);
                }
                AnnotationMirror r = find(m, P + "Reference");
                if (r != null) refs.add(methodRef(t, m, r));
            } else if (e.getKind() == ElementKind.CONSTRUCTOR) {
                ExecutableElement m = (ExecutableElement) e;
                if (find(m, P + "Activate") != null) {
                    List<? extends VariableElement> ps = m.getParameters();
                    init = Integer.toString(ps.size());
                    need(14);
                    lifecycleParams(m, props);
                    for (int i = 0; i < ps.size(); i++) {
                        AnnotationMirror r = find(ps.get(i), P + "Reference");
                        if (r != null) refs.add(paramRef(ps.get(i), i, r));
                    }
                }
            } else if (e.getKind() == ElementKind.FIELD) {
                AnnotationMirror r = find(e, P + "Reference");
                if (r != null) refs.add(fieldRef((VariableElement) e, r));
            }
        }
        // lookup-strategy references given in @Component(reference = ...)
        List<AnnotationValue> lr = list(c, "reference");
        if (lr != null) {
            for (AnnotationValue v : lr) {
                AnnotationMirror r = (AnnotationMirror) v.getValue();
                Ref x = new Ref();
                x.name = str(r, "name");
                x.iface = binary((TypeMirror) val(r, "service"));
                fillRef(x, r);
                refs.add(x);
            }
        }
        Collections.sort(refs);

        // property = {"name[:type]=value", ...}
        List<AnnotationValue> pv = list(c, "property");
        if (pv != null) {
            LinkedHashMap<String, Prop> el = new LinkedHashMap<>();
            for (AnnotationValue v : pv) {
                String s = v.getValue().toString();
                int eq = s.indexOf('=');
                String k = s.substring(0, eq).trim(), value = s.substring(eq + 1);
                String type = "String";
                int col = k.indexOf(':');
                if (col > 0) {
                    type = k.substring(col + 1).trim();
                    k = k.substring(0, col).trim();
                }
                Prop p = el.get(k);
                if (p == null) {
                    p = new Prop();
                    p.name = k;
                    p.type = type;
                    el.put(k, p);
                } else {
                    p.multi = true;
                }
                p.values.add(value);
            }
            props.putAll(el);
        }
        List<String> propertiesEntries = new ArrayList<>();
        List<AnnotationValue> pfv = list(c, "properties");
        if (pfv != null) for (AnnotationValue v : pfv) propertiesEntries.add(v.getValue().toString());

        String scope = enm(c, "scope");
        Object servicefactory = val(c, "servicefactory");
        if (scope != null && !scope.equals("DEFAULT")) need(13);
        if (val(c, "factoryProperty") != null || val(c, "factoryProperties") != null) need(14);

        // ----------------------------------------------------------- output
        StringBuilder x = new StringBuilder();
        x.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
        x.append("<scr:component xmlns:scr=\"http://www.osgi.org/xmlns/scr/v1.").append(version % 10).append(".0\"");
        attr(x, "name", cname);
        String cp = enm(c, "configurationPolicy");
        if (cp != null) attr(x, "configuration-policy", cp.toLowerCase(Locale.ROOT));
        attr(x, "enabled", str(c, "enabled"));
        attr(x, "factory", str(c, "factory"));
        attr(x, "immediate", str(c, "immediate"));
        attr(x, "activate", activate);
        attr(x, "deactivate", deactivate);
        attr(x, "modified", modified);
        List<AnnotationValue> pids = list(c, "configurationPid");
        if (pids != null) {
            StringBuilder s = new StringBuilder();
            for (AnnotationValue v : pids) {
                if (s.length() > 0) s.append(' ');
                s.append(v.getValue().toString().equals("$") ? cname : v.getValue().toString());
            }
            attr(x, "configuration-pid", s.toString());
        }
        attr(x, "init", init);
        x.append(">\n");
        for (Prop p : props.values()) {
            x.append("  <property");
            attr(x, "name", p.name);
            attr(x, "type", p.type);
            if (p.multi) {
                x.append(">").append(esc(String.join("\n", p.values))).append("</property>\n");
            } else {
                attr(x, "value", p.values.get(0));
                x.append("/>\n");
            }
        }
        for (String e : propertiesEntries) {
            x.append("  <properties");
            attr(x, "entry", e);
            x.append("/>\n");
        }
        if (!services.isEmpty()) {
            x.append("  <service");
            if (scope != null && !scope.equals("DEFAULT")) attr(x, "scope", scope.toLowerCase(Locale.ROOT));
            else if (Boolean.TRUE.equals(servicefactory)) attr(x, "servicefactory", "true");
            x.append(">\n");
            for (String s : services) {
                x.append("    <provide");
                attr(x, "interface", s);
                x.append("/>\n");
            }
            x.append("  </service>\n");
        }
        for (Ref r : refs) {
            x.append("  <reference");
            attr(x, "name", r.name);
            attr(x, "cardinality", r.cardinality);
            attr(x, "policy", r.policy);
            attr(x, "interface", r.iface);
            attr(x, "target", r.target);
            attr(x, "bind", r.bind);
            attr(x, "unbind", r.unbind);
            attr(x, "updated", r.updated);
            attr(x, "policy-option", r.policyOption);
            attr(x, "scope", r.scope);
            attr(x, "field", r.field);
            attr(x, "field-option", r.fieldOption);
            attr(x, "field-collection-type", r.fieldCollectionType);
            attr(x, "parameter", r.parameter);
            x.append("/>\n");
        }
        x.append("  <implementation");
        attr(x, "class", processingEnv.getElementUtils().getBinaryName(t).toString());
        x.append("/>\n");
        x.append("</scr:component>\n");
        // the namespace may have been raised while the references were built
        String out = x.toString().replaceFirst("scr/v1\\.\\d\\.0", "scr/v1." + (version % 10) + ".0");

        String dir = processingEnv.getOptions().getOrDefault("jb.ds.path", "OSGI-INF");
        String path = dir + "/" + cname + ".xml";
        try {
            FileObject fo = processingEnv.getFiler().createResource(StandardLocation.CLASS_OUTPUT, "", path, t);
            try (Writer w = new OutputStreamWriter(fo.openOutputStream(), StandardCharsets.UTF_8)) {
                w.write(out);
            }
            written.add(path);
        } catch (IOException ex) {
            error(t, "cannot write " + path + ": " + ex);
        }
    }

    static void attr(StringBuilder x, String n, String v) {
        if (v == null) return;
        x.append(' ').append(n).append("=\"").append(esc(v)).append('"');
    }

    static String esc(String s) {
        StringBuilder b = new StringBuilder();
        for (char ch : s.toCharArray()) {
            switch (ch) {
                case '&': b.append("&amp;"); break;
                case '<': b.append("&lt;"); break;
                case '>': b.append("&gt;"); break;
                case '"': b.append("&quot;"); break;
                default: b.append(ch);
            }
        }
        return b.toString();
    }

    // --------------------------------------------------------- references

    static String card(String c) {
        switch (c) {
            case "OPTIONAL": return "0..1";
            case "MANDATORY": return "1..1";
            case "MULTIPLE": return "0..n";
            case "AT_LEAST_ONE": return "1..n";
            default: return c;
        }
    }

    void fillRef(Ref r, AnnotationMirror a) {
        String c = enm(a, "cardinality");
        if (c != null) r.cardinality = card(c);
        String p = enm(a, "policy");
        if (p != null) r.policy = p.toLowerCase(Locale.ROOT);
        String t = str(a, "target");
        if (t != null && !t.isEmpty()) r.target = t;
        String po = enm(a, "policyOption");
        if (po != null) {
            r.policyOption = po.toLowerCase(Locale.ROOT);
            need(12 > version ? 12 : version);
        }
        String s = enm(a, "scope");
        if (s != null) r.scope = s.toLowerCase(Locale.ROOT);
        String u = str(a, "updated");
        if (u != null && !u.equals("-")) r.updated = u;
    }

    TypeMirror serviceType(TypeMirror t) {
        if (t.getKind() == TypeKind.DECLARED) {
            String n = binary(t);
            List<? extends TypeMirror> args = ((DeclaredType) t).getTypeArguments();
            if ((n.equals("org.osgi.framework.ServiceReference")
                    || n.equals(P.replace("annotations.", "ComponentServiceObjects"))
                    || n.equals("org.osgi.service.component.ComponentServiceObjects"))
                    && !args.isEmpty()) {
                TypeMirror a = args.get(0);
                if (a.getKind() == TypeKind.WILDCARD) {
                    TypeMirror b = ((WildcardType) a).getExtendsBound();
                    return b == null ? a : b;
                }
                return a;
            }
        }
        return t;
    }

    Ref methodRef(TypeElement owner, ExecutableElement m, AnnotationMirror a) {
        Ref r = new Ref();
        String mn = m.getSimpleName().toString();
        r.bind = mn;
        String n = str(a, "name");
        if (n == null) {
            n = mn;
            for (String pre : new String[] {"bind", "set", "add"}) {
                if (mn.startsWith(pre) && mn.length() > pre.length()) {
                    n = mn.substring(pre.length());
                    break;
                }
            }
        }
        r.name = n;
        Object sv = val(a, "service");
        if (sv != null) {
            r.iface = binary((TypeMirror) sv);
        } else {
            for (VariableElement p : m.getParameters()) {
                String pt = binary(p.asType());
                if (pt.equals("java.util.Map")) continue;
                r.iface = binary(serviceType(p.asType()));
                break;
            }
        }
        fillRef(r, a);
        String ub = str(a, "unbind");
        if (ub != null) {
            if (!ub.equals("-")) r.unbind = ub;
        } else {
            // bnd: the unbind method must take the same parameters as the bind method
            String cand = mn.startsWith("add") ? "remove" + mn.substring(3) : "un" + mn;
            for (Element e : owner.getEnclosedElements()) {
                if (e.getKind() == ElementKind.METHOD && e.getSimpleName().contentEquals(cand)
                        && sameParams((ExecutableElement) e, m)) {
                    r.unbind = cand;
                    break;
                }
            }
        }
        if (r.updated == null && val(a, "updated") == null) {
            String cand = "updated" + n;
            for (Element e : owner.getEnclosedElements()) {
                if (e.getKind() == ElementKind.METHOD && e.getSimpleName().contentEquals(cand)) {
                    r.updated = cand;
                    need(12);
                    break;
                }
            }
        }
        return r;
    }

    boolean sameParams(ExecutableElement a, ExecutableElement b) {
        List<? extends VariableElement> pa = a.getParameters(), pb = b.getParameters();
        if (pa.size() != pb.size() || pa.isEmpty()) return false;
        Types tu = processingEnv.getTypeUtils();
        for (int i = 0; i < pa.size(); i++) {
            if (!tu.isSameType(tu.erasure(pa.get(i).asType()), tu.erasure(pb.get(i).asType()))) return false;
        }
        return true;
    }

    String collectionType(TypeMirror elem) {
        String n = binary(elem);
        switch (n) {
            case "org.osgi.framework.ServiceReference": return "reference";
            case "org.osgi.service.component.ComponentServiceObjects": return "serviceobjects";
            case "java.util.Map": return "properties";
            case "java.util.Map$Entry": return "tuple";
            default: return null;
        }
    }

    Ref fieldRef(VariableElement f, AnnotationMirror a) {
        Ref r = new Ref();
        String n = str(a, "name");
        r.name = n == null ? f.getSimpleName().toString() : n;
        r.field = f.getSimpleName().toString();
        TypeMirror t = f.asType();
        String tn = binary(t);
        boolean collection = tn.equals("java.util.Collection") || tn.equals("java.util.List");
        TypeMirror elem = t;
        if (collection && t.getKind() == TypeKind.DECLARED && !((DeclaredType) t).getTypeArguments().isEmpty()) {
            elem = ((DeclaredType) t).getTypeArguments().get(0);
            if (elem.getKind() == TypeKind.WILDCARD) {
                TypeMirror b = ((WildcardType) elem).getExtendsBound();
                if (b != null) elem = b;
            }
        }
        Object sv = val(a, "service");
        r.iface = sv != null ? binary((TypeMirror) sv) : binary(serviceType(elem));
        fillRef(r, a);
        boolean dyn = f.getModifiers().contains(Modifier.VOLATILE);
        if (r.policy == null && dyn) r.policy = "dynamic";
        if (collection) {
            if (r.cardinality == null) r.cardinality = "0..n";
            String ct = collectionType(elem);
            if (ct != null) r.fieldCollectionType = ct;
            String fo = enm(a, "fieldOption");
            if (fo != null) r.fieldOption = fo.toLowerCase(Locale.ROOT);
            else if ("dynamic".equals(r.policy) && !f.getModifiers().contains(Modifier.VOLATILE)) r.fieldOption = "update";
        } else {
            String fo = enm(a, "fieldOption");
            if (fo != null) r.fieldOption = fo.toLowerCase(Locale.ROOT);
        }
        if (tn.equals("java.util.Optional")) need(15);
        return r;
    }

    Ref paramRef(VariableElement p, int i, AnnotationMirror a) {
        Ref r = new Ref();
        String n = str(a, "name");
        r.name = n == null ? String.format("$%03d", i) : n;
        r.parameter = Integer.toString(i);
        TypeMirror t = p.asType();
        String tn = binary(t);
        boolean collection = tn.equals("java.util.Collection") || tn.equals("java.util.List");
        TypeMirror elem = t;
        if (collection && !((DeclaredType) t).getTypeArguments().isEmpty()) {
            elem = ((DeclaredType) t).getTypeArguments().get(0);
        }
        Object sv = val(a, "service");
        r.iface = sv != null ? binary((TypeMirror) sv) : binary(serviceType(elem));
        fillRef(r, a);
        if (collection) {
            if (r.cardinality == null) r.cardinality = "0..n";
            String ct = collectionType(elem);
            if (ct != null) r.fieldCollectionType = ct;
        }
        return r;
    }

    // -------------------------------------------------- property types

    boolean isPropertyType(AnnotationMirror m) {
        return find(m.getAnnotationType().asElement(), P + "ComponentPropertyType") != null;
    }

    /** activate/modified/constructor parameters typed with property types contribute their defaults */
    void lifecycleParams(ExecutableElement m, LinkedHashMap<String, Prop> props) {
        for (VariableElement p : m.getParameters()) {
            TypeMirror t = p.asType();
            if (t.getKind() != TypeKind.DECLARED) continue;
            Element te = ((DeclaredType) t).asElement();
            if (te.getKind() != ElementKind.ANNOTATION_TYPE) continue;
            for (Element e : te.getEnclosedElements()) {
                if (e.getKind() != ElementKind.METHOD) continue;
                ExecutableElement ee = (ExecutableElement) e;
                AnnotationValue d = ee.getDefaultValue();
                if (d == null) continue;
                String name = prefix(te) + elementName(ee.getSimpleName().toString());
                if (props.containsKey(name)) continue;
                Prop pr = prop(name, ee.getReturnType(), d);
                if (pr != null) props.put(name, pr);
            }
        }
    }

    String prefix(Element annotationType) {
        for (Element e : annotationType.getEnclosedElements()) {
            if (e.getKind() == ElementKind.FIELD && e.getSimpleName().contentEquals("PREFIX_")) {
                Object v = ((VariableElement) e).getConstantValue();
                if (v != null) return v.toString();
            }
        }
        return "";
    }

    static String elementName(String n) {
        // DS 1.4 112.8.2.1: $_$ -> '-', $$ -> '$', $ removed, __ -> '_', _ -> '.'
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < n.length(); i++) {
            char c = n.charAt(i);
            if (c == '$') {
                if (n.startsWith("$_$", i)) { b.append('-'); i += 2; }
                else if (n.startsWith("$$", i)) { b.append('$'); i += 1; }
            } else if (c == '_') {
                if (n.startsWith("__", i)) { b.append('_'); i += 1; }
                else b.append('.');
            } else {
                b.append(c);
            }
        }
        return b.toString();
    }

    static String typeName(String simple) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < simple.length(); i++) {
            char c = simple.charAt(i);
            if (i > 0 && Character.isUpperCase(c)) {
                char prev = simple.charAt(i - 1);
                boolean nextLower = i + 1 < simple.length() && Character.isLowerCase(simple.charAt(i + 1));
                if (Character.isLowerCase(prev) || (Character.isUpperCase(prev) && nextLower)) b.append('.');
            }
            b.append(Character.toLowerCase(c));
        }
        return b.toString();
    }

    void propertyType(AnnotationMirror m, LinkedHashMap<String, Prop> props, boolean defaultsOnly) {
        Element te = m.getAnnotationType().asElement();
        List<ExecutableElement> els = new ArrayList<>();
        for (Element e : te.getEnclosedElements()) {
            if (e.getKind() == ElementKind.METHOD) els.add((ExecutableElement) e);
        }
        String pre = prefix(te);
        Map<? extends ExecutableElement, ? extends AnnotationValue> vals =
                processingEnv.getElementUtils().getElementValuesWithDefaults(m);
        if (els.isEmpty()) {
            // marker annotation: Boolean.TRUE
            Prop p = new Prop();
            p.name = pre + typeName(te.getSimpleName().toString());
            p.type = "Boolean";
            p.values.add("true");
            props.put(p.name, p);
            return;
        }
        boolean single = els.size() == 1 && els.get(0).getSimpleName().contentEquals("value");
        for (ExecutableElement e : els) {
            AnnotationValue v = vals.get(e);
            if (v == null) continue;
            String name = single ? pre + typeName(te.getSimpleName().toString())
                    : pre + elementName(e.getSimpleName().toString());
            Prop p = prop(name, e.getReturnType(), v);
            if (p != null) props.put(name, p);
        }
    }

    @SuppressWarnings("unchecked")
    Prop prop(String name, TypeMirror rt, AnnotationValue v) {
        Prop p = new Prop();
        p.name = name;
        TypeMirror et = rt;
        if (rt.getKind() == TypeKind.ARRAY) {
            p.multi = true;
            et = ((ArrayType) rt).getComponentType();
            for (AnnotationValue x : (List<AnnotationValue>) v.getValue()) p.values.add(scalar(x.getValue()));
        } else {
            p.values.add(scalar(v.getValue()));
        }
        switch (et.getKind()) {
            case BOOLEAN: p.type = "Boolean"; break;
            case BYTE: p.type = "Byte"; break;
            case CHAR: p.type = "Character"; break;
            case SHORT: p.type = "Short"; break;
            case INT: p.type = "Integer"; break;
            case LONG: p.type = "Long"; break;
            case FLOAT: p.type = "Float"; break;
            case DOUBLE: p.type = "Double"; break;
            default: p.type = "String";
        }
        if (p.type.equals("Character")) {
            List<String> ints = new ArrayList<>();
            for (String s : p.values) ints.add(Integer.toString(s.charAt(0)));
            p.values = ints;
        }
        return p;
    }

    String scalar(Object o) {
        if (o instanceof TypeMirror) return binary((TypeMirror) o);
        if (o instanceof VariableElement) return ((VariableElement) o).getSimpleName().toString();
        return String.valueOf(o);
    }
}
