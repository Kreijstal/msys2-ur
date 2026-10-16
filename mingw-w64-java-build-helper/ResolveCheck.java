/*
 * OSGi resolution check for jb_osgi_resolvecheck: installs bundles into an
 * Equinox framework (the org.eclipse.osgi jar on the class path), resolves
 * them and reports every bundle that stays INSTALLED with the framework's
 * explanation.  Optionally starts the bundles given with --start.
 *
 *   java -cp org.eclipse.osgi.jar;. jb.ResolveCheck [--allow REGEX] [--start BSN]...
 *        [--check N] STORAGE-DIR BUNDLE-JAR-OR-DIR...
 *   only the first N bundles (default all) are reported and must resolve;
 *   the others are their dependencies.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package jb;

import java.io.File;
import java.util.*;
import java.util.regex.Pattern;
import org.osgi.framework.Bundle;
import org.osgi.framework.BundleContext;
import org.osgi.framework.BundleException;
import org.osgi.framework.Constants;
import org.osgi.framework.launch.Framework;
import org.osgi.framework.launch.FrameworkFactory;
import org.osgi.framework.wiring.FrameworkWiring;

public class ResolveCheck {
    public static void main(String[] args) throws Exception {
        Pattern allow = null;
        List<String> start = new ArrayList<>();
        int check = Integer.MAX_VALUE;
        int i = 0;
        while (args[i].startsWith("--")) {
            if (args[i].equals("--allow")) allow = Pattern.compile(args[i + 1]);
            else if (args[i].equals("--start")) start.add(args[i + 1]);
            else if (args[i].equals("--check")) check = Integer.parseInt(args[i + 1]);
            i += 2;
        }
        File storage = new File(args[i++]);
        Map<String, String> cfg = new HashMap<>();
        cfg.put(Constants.FRAMEWORK_STORAGE, storage.getAbsolutePath());
        cfg.put(Constants.FRAMEWORK_STORAGE_CLEAN, Constants.FRAMEWORK_STORAGE_CLEAN_ONFIRSTINIT);
        cfg.put("osgi.console", "");
        cfg.put("eclipse.ignoreApp", "true");
        cfg.put("osgi.noShutdown", "false");
        cfg.put("osgi.instance.area", new File(storage, "instance").toURI().toString());
        FrameworkFactory ff = ServiceLoader.load(FrameworkFactory.class).iterator().next();
        Framework fw = ff.newFramework(cfg);
        fw.init();
        BundleContext ctx = fw.getBundleContext();
        List<Bundle> bundles = new ArrayList<>();
        for (; i < args.length; i++) {
            File f = new File(args[i]);
            bundles.add(ctx.installBundle("reference:" + f.toURI().toString()));
        }
        fw.start();
        fw.adapt(FrameworkWiring.class).resolveBundles(bundles);
        int bad = 0, n = 0;
        for (Bundle b : bundles) {
            boolean checked = n++ < check;
            String id = b.getSymbolicName() + "_" + b.getVersion();
            boolean fragment = b.getHeaders("").get(Constants.FRAGMENT_HOST) != null;
            if (b.getState() == Bundle.INSTALLED) {
                String why = "";
                if (!fragment) {
                    try {
                        b.start(Bundle.START_TRANSIENT);
                    } catch (BundleException e) {
                        why = e.getMessage().replace('\n', ' ');
                    }
                }
                boolean ok = !checked || allow != null && allow.matcher(b.getSymbolicName()).find();
                System.out.println((ok ? "INSTALLED (not checked) " : "INSTALLED ") + id + " " + why);
                if (!ok) bad++;
            } else if (checked) {
                System.out.println("RESOLVED  " + id);
            }
        }
        for (String s : start) {
            for (Bundle b : bundles) {
                if (s.equals(b.getSymbolicName())) {
                    try {
                        b.start();
                        System.out.println("STARTED   " + s + " state=" + b.getState());
                    } catch (BundleException e) {
                        System.out.println("FAILED    " + s + ": " + e);
                        bad++;
                    }
                }
            }
        }
        fw.stop();
        fw.waitForStop(30000);
        System.out.println("ResolveCheck: " + Math.min(check, bundles.size()) + " bundles checked (" + bundles.size() + " installed), " + bad + " problem(s)");
        System.exit(bad == 0 ? 0 : 1);
    }
}
