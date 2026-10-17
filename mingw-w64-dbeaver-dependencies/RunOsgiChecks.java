/* SPDX-License-Identifier: MIT */
import java.nio.file.*;
import java.util.*;
import org.osgi.framework.*;
import org.osgi.framework.launch.*;
import org.osgi.framework.wiring.*;

public class RunOsgiChecks {
    public static void main(String[] args) throws Exception {
        Map<String, String> settings = new HashMap<>();
        settings.put(Constants.FRAMEWORK_STORAGE, args[1]);
        settings.put(Constants.FRAMEWORK_STORAGE_CLEAN, "onFirstInit");
        Framework framework = ServiceLoader.load(FrameworkFactory.class).iterator().next().newFramework(settings);
        try {
            framework.start();
            var context = framework.getBundleContext();
            List<Bundle> bundles = new ArrayList<>();
            try (var paths = Files.list(Path.of(args[0]))) {
                for (Path file : paths.sorted().toList()) {
                    String name = file.getFileName().toString();
                    if (name.startsWith("org.eclipse.osgi_")) continue;
                    if (Files.isDirectory(file) && !Files.exists(file.resolve("META-INF/MANIFEST.MF"))) continue;
                    if (!Files.isDirectory(file) && !name.endsWith(".jar")) continue;
                    bundles.add(context.installBundle("reference:" + file.toUri().toASCIIString()));
                }
            }
            Bundle test = context.installBundle(Path.of(args[2]).toUri().toASCIIString());
            bundles.add(test);
            FrameworkWiring wiring = framework.adapt(FrameworkWiring.class);
            wiring.resolveBundles(bundles);
            int unresolved = 0;
            for (Bundle bundle : bundles) {
                if (bundle.getState() == Bundle.INSTALLED) {
                    System.err.println("UNRESOLVED " + bundle.getSymbolicName());
                    unresolved++;
                }
            }
            if (unresolved != 0) throw new AssertionError(unresolved + " unresolved bundles");
            test.start();
            System.out.println("PASS: " + bundles.size() + " installed bundles resolved; dependency consumer activated");
        } finally {
            framework.stop();
            framework.waitForStop(15000);
        }
    }
}
