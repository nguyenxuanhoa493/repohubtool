package org.recompile.freej2me;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.OutputStreamWriter;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import org.recompile.mobile.Mobile;

public class SDLConfig {
    private int width;
    private int height;
    private File file;
    private String configPath = "";
    private String configFile = "";
    HashMap<String, String> settings = new HashMap<>(6);

    public SDLConfig() {
        this.width = Mobile.getPlatform().lcdWidth;
        this.height = Mobile.getPlatform().lcdHeight;
    }

    private static String getDefaultPhoneMode() {
        // 1. Uu tien doc System Property (-Dfreej2me.phone=...)
        String prop = System.getProperty("freej2me.phone");
        if (prop != null && !prop.trim().isEmpty()) {
            return prop.trim().toLowerCase();
        }
        // 2. Doc file default_phone.cfg tu cac vi tri tren thiet bi
        String[] paths = new String[]{
            "default_phone.cfg",
            "../default_phone.cfg",
            "/mnt/SDCARD/Emus/JAVA/default_phone.cfg",
            "/mnt/SDCARD/Emus/JAVA/zulu17/bin/default_phone.cfg"
        };
        for (String p : paths) {
            try {
                File f = new File(p);
                if (f.isFile()) {
                    try (BufferedReader reader = new BufferedReader(new FileReader(f))) {
                        String line = reader.readLine();
                        if (line != null && !line.trim().isEmpty()) {
                            return line.trim().toLowerCase();
                        }
                    }
                }
            } catch (Exception ignored) {}
        }
        // Mac dinh toan he thong la Nokia ("n")
        return "n";
    }

    public void init(String suiteName) {
        this.configPath = Mobile.getPlatform().dataPath + "./config/" + suiteName;
        this.configFile = this.configPath + "/game.conf";
        try {
            Files.createDirectories(Paths.get(this.configPath));
        } catch (Exception e) {
            System.out.println("Problem Creating Config Path " + this.configPath);
            System.out.println(e.getMessage());
        }
        this.file = new File(this.configFile);
        if (!this.file.exists()) {
            try {
                this.file.createNewFile();
                this.settings.put("width", "" + this.width);
                this.settings.put("height", "" + this.height);
                this.settings.put("sound", "100");
                this.settings.put("phone", getDefaultPhoneMode());
                this.settings.put("fps", "60");
                this.saveConfig();
            } catch (Exception e) {
                System.out.println("Problem Opening Config " + this.configFile);
                System.out.println(e.getMessage());
            }
        }
        try (BufferedReader reader = new BufferedReader(new FileReader(this.file))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(":");
                if (parts.length == 2) {
                    parts[0] = parts[0].trim();
                    parts[1] = parts[1].trim();
                    if (!parts[0].isEmpty() && !parts[1].isEmpty()) {
                        this.settings.put(parts[0], parts[1]);
                    }
                }
            }
            if (!this.settings.containsKey("width")) {
                this.settings.put("width", "" + this.width);
            }
            if (!this.settings.containsKey("height")) {
                this.settings.put("height", "" + this.height);
            }
            if (!this.settings.containsKey("sound")) {
                this.settings.put("sound", "100");
            }
            if (!this.settings.containsKey("phone")) {
                this.settings.put("phone", getDefaultPhoneMode());
            }
            if (!this.settings.containsKey("fps")) {
                this.settings.put("fps", "60");
            }
            int parsedW = Integer.parseInt(this.settings.get("width"));
            int parsedH = Integer.parseInt(this.settings.get("height"));
            if (this.width != parsedW || this.height != parsedH) {
                this.width = parsedW;
                this.height = parsedH;
            }
        } catch (Exception e) {
            System.out.println("Problem Reading Config: " + this.configFile);
            System.out.println(e.getMessage());
        }
    }

    public void saveConfig() {
        try (BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(this.file)))) {
            for (String key : this.settings.keySet()) {
                writer.write(key + ":" + this.settings.get(key) + "\n");
            }
        } catch (Exception e) {
            System.out.println("Problem Opening Config " + this.configFile);
            System.out.println(e.getMessage());
        }
    }
}
