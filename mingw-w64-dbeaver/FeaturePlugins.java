/* SPDX-License-Identifier: MIT */
import java.nio.file.*;
import java.util.*;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.*;

/**
 * Prints the plug-ins of a feature and the features it includes, for one
 * platform (os/ws/arch filters as p2 applies them). Included features that
 * are not in FEATURES-DIR are printed as "feature:ID".
 *
 *   java FeaturePlugins.java FEATURES-DIR FEATURE-ID OS WS ARCH
 */
public class FeaturePlugins {
    static final Set<String> seen = new LinkedHashSet<>();
    static final Set<String> out = new LinkedHashSet<>();
    static Path dir;
    static String os, ws, arch;

    public static void main(String[] args) throws Exception {
        dir = Path.of(args[0]);
        os = args[2];
        ws = args[3];
        arch = args[4];
        walk(args[1]);
        out.forEach(System.out::println);
    }

    static boolean matches(Element e, String attr, String value) {
        String v = e.getAttribute(attr);
        return v.isEmpty() || Arrays.asList(v.split(",")).contains(value);
    }

    static void walk(String id) throws Exception {
        if (!seen.add(id)) return;
        Path xml = dir.resolve(id).resolve("feature.xml");
        if (!Files.exists(xml)) {
            out.add("feature:" + id);
            return;
        }
        Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(xml.toFile());
        NodeList nodes = doc.getDocumentElement().getChildNodes();
        for (int i = 0; i < nodes.getLength(); i++) {
            if (!(nodes.item(i) instanceof Element e)) continue;
            if (!matches(e, "os", os) || !matches(e, "ws", ws) || !matches(e, "arch", arch)) continue;
            switch (e.getTagName()) {
                case "includes" -> walk(e.getAttribute("id"));
                case "plugin" -> out.add(e.getAttribute("id"));
                default -> { }
            }
        }
    }
}
