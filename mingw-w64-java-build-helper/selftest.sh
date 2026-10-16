#!/usr/bin/env bash
# Self-test of the javabuild annotation processors: compiles a fake plugin
# and component set against stub annotation types and checks the generated
# plugin.xml and components.xml.
#   selftest.sh <javabuild.jar> <workdir>
set -euo pipefail
jar=$1
w=$2
rm -rf "${w:?}"
mkdir -p "$w"
cd "$w"
mk() { mkdir -p "$(dirname "$1")"; cat > "$1"; }
mk res/META-INF/plexus/components.xml <<'END_OF_FILE'
<?xml version="1.0" encoding="UTF-8"?>
<component-set>
  <components>
    <component>
      <role>t.Svc</role>
      <role-hint>handwritten</role-hint>
      <implementation>t.DefaultSvc</implementation>
    </component>
  </components>
</component-set>
END_OF_FILE
mk src/t/Base.java <<'END_OF_FILE'
package t;
import org.apache.maven.plugins.annotations.*;
public abstract class Base {
    /** Where the output goes. */
    @Parameter(defaultValue = "${project.build.directory}", required = true)
    protected java.io.File outputDirectory;
    @Parameter(property = "skip", defaultValue = "false")
    protected boolean skip;
}
END_OF_FILE
mk src/t/DefaultSvc.java <<'END_OF_FILE'
package t;
import org.codehaus.plexus.component.annotations.*;
@Component(role = Svc.class, hint = "fast", instantiationStrategy = "per-lookup")
public class DefaultSvc implements Svc {
    @Requirement private Runnable r;
    @Requirement(role = Svc.class) private java.util.Map<String, Svc> all;
}
END_OF_FILE
mk src/t/HelloMojo.java <<'END_OF_FILE'
package t;
import java.util.List;
import org.apache.maven.plugins.annotations.*;
/** Says hello. */
@Mojo(name = "hello", defaultPhase = LifecyclePhase.PROCESS_TEST_RESOURCES,
      requiresDependencyResolution = ResolutionScope.COMPILE_PLUS_RUNTIME, threadSafe = true)
public class HelloMojo extends Base {
    @Parameter(property = "hello.names", alias = "people")
    private List<String> names;
    @Component(hint = "x")
    private Runnable runner;
    public static class Inner {}
    @Parameter
    private Inner inner;
}
END_OF_FILE
mk src/t/OldSvc.java <<'END_OF_FILE'
package t;
/**
 * Old style component. More text.
 *
 * @plexus.component role="t.Svc" role-hint="old"
 *   instantiation-strategy="per-lookup"
 */
public class OldSvc implements Svc {
    /** @plexus.requirement role-hint="fast" */
    private Svc delegate;
}
END_OF_FILE
mk src/t/Svc.java <<'END_OF_FILE'
package t;
public interface Svc {}
END_OF_FILE
mk stubs/org/apache/maven/plugins/annotations/Component.java <<'END_OF_FILE'
package org.apache.maven.plugins.annotations;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target(ElementType.FIELD)
public @interface Component { Class<?> role() default Object.class; String hint() default ""; }
END_OF_FILE
mk stubs/org/apache/maven/plugins/annotations/LifecyclePhase.java <<'END_OF_FILE'
package org.apache.maven.plugins.annotations;
public enum LifecyclePhase { NONE, PROCESS_TEST_RESOURCES, COMPILE }
END_OF_FILE
mk stubs/org/apache/maven/plugins/annotations/Mojo.java <<'END_OF_FILE'
package org.apache.maven.plugins.annotations;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target(ElementType.TYPE)
public @interface Mojo {
    String name();
    LifecyclePhase defaultPhase() default LifecyclePhase.NONE;
    ResolutionScope requiresDependencyResolution() default ResolutionScope.NONE;
    boolean threadSafe() default false;
}
END_OF_FILE
mk stubs/org/apache/maven/plugins/annotations/Parameter.java <<'END_OF_FILE'
package org.apache.maven.plugins.annotations;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target({ElementType.FIELD, ElementType.METHOD})
public @interface Parameter {
    String name() default ""; String alias() default ""; String property() default "";
    String defaultValue() default ""; boolean required() default false; boolean readonly() default false;
}
END_OF_FILE
mk stubs/org/apache/maven/plugins/annotations/ResolutionScope.java <<'END_OF_FILE'
package org.apache.maven.plugins.annotations;
public enum ResolutionScope { NONE, COMPILE_PLUS_RUNTIME, TEST }
END_OF_FILE
mk stubs/org/codehaus/plexus/component/annotations/Component.java <<'END_OF_FILE'
package org.codehaus.plexus.component.annotations;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target(ElementType.TYPE)
public @interface Component { Class<?> role(); String hint() default ""; String instantiationStrategy() default ""; }
END_OF_FILE
mk stubs/org/codehaus/plexus/component/annotations/Requirement.java <<'END_OF_FILE'
package org.codehaus.plexus.component.annotations;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target(ElementType.FIELD)
public @interface Requirement { Class<?> role() default Object.class; String hint() default ""; boolean optional() default false; }
END_OF_FILE
mk plugin.properties <<'END_OF_FILE'
groupId=t
artifactId=hello-maven-plugin
version=1.0
goalPrefix=hello
name=Hello
description=Test plugin
dependency.0=x:y:jar:2
END_OF_FILE
mk res/META-INF/plexus/extra.xml <<'END_OF_FILE'
<?xml version="1.0" encoding="UTF-8"?>
<component-set>
  <components>
    <component>
      <role>t.Extra</role>
      <implementation>t.DefaultSvc</implementation>
    </component>
  </components>
</component-set>
END_OF_FILE
win() { cygpath -m "$@" 2>/dev/null || echo "$@"; }
sep=';'; command -v cygpath >/dev/null || sep=':'
mkdir -p stubs-out out
javac -nowarn -d stubs-out $(find stubs -name '*.java')
cp -r res/. out/
javac -nowarn -cp stubs-out -processorpath "$(win "$jar")" \
  -processor jb.MojoDescriptorProcessor,jb.PlexusComponentsProcessor \
  -Ajb.plugin="$(win "$PWD/plugin.properties")" -d out $(find src -name '*.java')
p=out/META-INF/maven/plugin.xml
c=out/META-INF/plexus/components.xml
fail=0
expect() { grep -qF -- "$2" "$1" || { echo "selftest: missing in $1: $2"; fail=1; }; }
expect $p '<goal>hello</goal>'
expect $p '<phase>process-test-resources</phase>'
expect $p '<requiresDependencyResolution>compile+runtime</requiresDependencyResolution>'
expect $p '<threadSafe>true</threadSafe>'
expect $p '<outputDirectory implementation="java.io.File" default-value="${project.build.directory}"/>'
expect $p '<names implementation="java.util.List">${hello.names}</names>'
expect $p '<type>java.util.List</type>'
expect $p '<alias>people</alias>'
expect $p '<description>Where the output goes.</description>'
expect $p '<role-hint>x</role-hint>'
expect $p '<artifactId>y</artifactId>'
expect $c '<role-hint>handwritten</role-hint>'
expect $c '<role-hint>old</role-hint>'
expect $c '<role-hint>fast</role-hint>'
expect $c '<field-name>delegate</field-name>'
expect $c '<field-name>all</field-name>'
expect $c '<instantiation-strategy>per-lookup</instantiation-strategy>'
expect $c '<role>t.Extra</role>'
# LoadCheck on the compiled classes
(cd out && jar cf ../t.jar t)
java -cp "$(win "$jar")" jb.LoadCheck "$(win "$PWD/t.jar")" "$(win "$PWD/stubs-out")"
# --- Declarative Services: jb.DsProcessor against stub DS annotations
mk ds/stubs/org/osgi/service/component/annotations/Component.java <<'END_OF_FILE'
package org.osgi.service.component.annotations;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target(ElementType.TYPE)
public @interface Component { String name() default ""; Class<?>[] service() default {}; String[] property() default {};
  boolean immediate() default false; }
END_OF_FILE
mk ds/stubs/org/osgi/service/component/annotations/Reference.java <<'END_OF_FILE'
package org.osgi.service.component.annotations;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target({ElementType.METHOD, ElementType.FIELD, ElementType.PARAMETER})
public @interface Reference { ReferenceCardinality cardinality() default ReferenceCardinality.MANDATORY;
  ReferencePolicy policy() default ReferencePolicy.STATIC; String unbind() default ""; }
END_OF_FILE
mk ds/stubs/org/osgi/service/component/annotations/ReferenceCardinality.java <<'END_OF_FILE'
package org.osgi.service.component.annotations;
public enum ReferenceCardinality { OPTIONAL, MANDATORY, MULTIPLE, AT_LEAST_ONE }
END_OF_FILE
mk ds/stubs/org/osgi/service/component/annotations/ReferencePolicy.java <<'END_OF_FILE'
package org.osgi.service.component.annotations;
public enum ReferencePolicy { STATIC, DYNAMIC }
END_OF_FILE
mk ds/stubs/org/osgi/service/component/annotations/Activate.java <<'END_OF_FILE'
package org.osgi.service.component.annotations;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target({ElementType.METHOD, ElementType.CONSTRUCTOR})
public @interface Activate {}
END_OF_FILE
mk ds/stubs/org/osgi/service/component/annotations/ComponentPropertyType.java <<'END_OF_FILE'
package org.osgi.service.component.annotations;
import java.lang.annotation.*;
@Retention(RetentionPolicy.CLASS) @Target(ElementType.ANNOTATION_TYPE)
public @interface ComponentPropertyType {}
END_OF_FILE
mk ds/src/d/Topics.java <<'END_OF_FILE'
package d;
@org.osgi.service.component.annotations.ComponentPropertyType
@java.lang.annotation.Retention(java.lang.annotation.RetentionPolicy.CLASS)
public @interface EventTopics { String[] value(); }
END_OF_FILE
mv ds/src/d/Topics.java ds/src/d/EventTopics.java
mk ds/src/d/Log.java <<'END_OF_FILE'
package d;
public interface Log {}
END_OF_FILE
mk ds/src/d/Comp.java <<'END_OF_FILE'
package d;
import org.osgi.service.component.annotations.*;
@Component(service = Runnable.class, property = "x:Integer=1")
@EventTopics("a/b")
public class Comp implements Runnable {
    @Reference private Log log;
    @Activate void activate() {}
    @Reference(cardinality = ReferenceCardinality.OPTIONAL, policy = ReferencePolicy.DYNAMIC)
    void setThing(Log l) {}
    void unsetThing(Log l) {}
    public void run() {}
}
END_OF_FILE
mkdir -p ds/stubs-out ds/out
javac -nowarn -d ds/stubs-out $(find ds/stubs -name '*.java')
javac -nowarn -cp ds/stubs-out -processorpath "$(win "$jar")" -processor jb.DsProcessor -d ds/out $(find ds/src -name '*.java')
cat > ds/expected.xml <<'END_OF_FILE'
<?xml version="1.0" encoding="UTF-8"?>
<scr:component xmlns:scr="http://www.osgi.org/xmlns/scr/v1.3.0" name="d.Comp" activate="activate">
  <property name="event.topics" type="String">a/b</property>
  <property name="x" type="Integer" value="1"/>
  <service>
    <provide interface="java.lang.Runnable"/>
  </service>
  <reference name="Thing" cardinality="0..1" policy="dynamic" interface="d.Log" bind="setThing" unbind="unsetThing"/>
  <reference name="log" interface="d.Log" field="log"/>
  <implementation class="d.Comp"/>
</scr:component>
END_OF_FILE
cmp -s ds/expected.xml ds/out/OSGI-INF/d.Comp.xml || { echo "selftest: DS description differs"; diff ds/expected.xml ds/out/OSGI-INF/d.Comp.xml; fail=1; }

# --- jb.Bnd: exports with versions and uses, imports of the class path
(cd ds/out && jar cf ../d.jar d)
printf 'Bundle-SymbolicName: d\nBundle-Version: 1.2.3\nExport-Package: d;version=1.2.3\n' > ds/d.bnd
java -cp "$(win "$jar")" jb.Bnd "$(win "$PWD/ds/d.jar")" "$(win "$PWD/ds/d.bnd")" "$(win "$PWD/ds/MANIFEST.MF")" ""
expect ds/MANIFEST.MF 'Bundle-SymbolicName: d'
tr -d '\r' < ds/MANIFEST.MF | sed ':a;N;$!ba;s/\n //g' | grep -q 'Export-Package: d;version="1.2.3"' \
  || { echo "selftest: jb.Bnd export"; cat ds/MANIFEST.MF; fail=1; }

exit $fail
