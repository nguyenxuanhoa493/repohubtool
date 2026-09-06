package org.recompile.freej2me;

import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import javax.microedition.lcdui.Display;
import javax.microedition.lcdui.Displayable;
import javax.microedition.lcdui.TextBox;
import org.recompile.mobile.Mobile;

/**
 * Hybrid On-Screen Virtual Keyboard and Quick Chat Macro overlay for FreeJ2ME on TrimUI devices.
 */
public class VirtualKeyboard {

    public static boolean active = false;

    private static final StringBuilder buffer = new StringBuilder();
    private static final List<String> quickPhrases = new ArrayList<>();
    private static boolean quickPhrasesLoaded = false;

    // Navigation: row -1 = Quick Bar, 0..3 = Keyboard rows, 4 = Action row
    private static int selRow = -1;
    private static int selCol = 0;
    private static int quickScroll = 0;

    private static boolean shift = false;
    private static boolean symMode = false;

    private static long cursorBlinkTime = 0;
    private static boolean cursorVisible = true;

    // Hotkey combo tracking
    private static volatile boolean selectHeld = false;
    private static volatile boolean startHeld = false;
    private static long lastToggleTime = 0;

    // Layouts
    private static final String[][] ROWS_LOWER = {
        {"1", "2", "3", "4", "5", "6", "7", "8", "9", "0"},
        {"q", "w", "e", "r", "t", "y", "u", "i", "o", "p"},
        {"a", "s", "d", "f", "g", "h", "j", "k", "l", "@"},
        {"z", "x", "c", "v", "b", "n", "m", ".", "_", "/"}
    };

    private static final String[][] ROWS_UPPER = {
        {"1", "2", "3", "4", "5", "6", "7", "8", "9", "0"},
        {"Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"},
        {"A", "S", "D", "F", "G", "H", "J", "K", "L", "@"},
        {"Z", "X", "C", "V", "B", "N", "M", ",", "-", "/"}
    };

    private static final String[][] ROWS_SYM = {
        {"!", "\"", "#", "$", "%", "&", "'", "(", ")", "*"},
        {"+", ",", "-", ".", "/", ":", ";", "<", "=", ">"},
        {"?", "[", "\\", "]", "^", "_", "`", "{", "|", "}"},
        {"~", "@", "$", "%", "*", "+", "=", "/", ":", ";"}
    };

    private static final String[] ACTION_LABELS = {
        "Shift", "Cách", "⌫ Xóa", "↵ Xong", "✕ Đóng"
    };

    // Color theme
    private static final Color BG_OVERLAY = new Color(11, 17, 32, 235);
    private static final Color BORDER_BOX = new Color(30, 41, 59);
    private static final Color PREVIEW_BG = new Color(15, 23, 42);
    private static final Color ACCENT_COLOR = new Color(56, 189, 248);
    private static final Color ACCENT_DIM = new Color(14, 116, 144);
    private static final Color KEY_BG = new Color(30, 41, 59);
    private static final Color KEY_TEXT = new Color(241, 245, 249);
    private static final Color MUTED_TEXT = new Color(148, 163, 184);

    private static Font customFont = null;

    static {
        loadQuickPhrases();
        loadFont();
    }

    private static void loadFont() {
        try {
            File fontFile = new File("font.ttf");
            if (fontFile.exists()) {
                customFont = Font.createFont(Font.TRUETYPE_FONT, fontFile);
            }
        } catch (Exception ignored) {}
    }

    public static synchronized void loadQuickPhrases() {
        quickPhrases.clear();
        File file = new File("quickchat.txt");
        if (!file.exists()) {
            file = new File("/mnt/SDCARD/Emus/JAVA/zulu17/bin/quickchat.txt");
        }

        if (file.exists()) {
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (!line.isEmpty() && !line.startsWith("#")) {
                        quickPhrases.add(line);
                    }
                }
            } catch (Exception ignored) {}
        }

        // If still empty, supply default sample phrases and write out default file
        if (quickPhrases.isEmpty()) {
            quickPhrases.add("taikhoan");
            quickPhrases.add("matkhau");
            quickPhrases.add("ok");
            quickPhrases.add("pt di");
            quickPhrases.add("doi xiu");
            quickPhrases.add("giao dich");
            quickPhrases.add("a");
            quickPhrases.add("hs");
            quickPhrases.add("td50");

            saveDefaultFile(file);
        }
        quickPhrasesLoaded = true;
    }

    private static void saveDefaultFile(File file) {
        try (OutputStreamWriter writer = new OutputStreamWriter(
                new FileOutputStream(file), StandardCharsets.UTF_8)) {
            writer.write("# Danh sach chuoi mau / Quick Chat\n");
            for (String phrase : quickPhrases) {
                writer.write(phrase + "\n");
            }
        } catch (Exception ignored) {}
    }

    public static void toggle() {
        if (active) {
            close();
        } else {
            open();
        }
    }

    public static void open() {
        if (!quickPhrasesLoaded) {
            loadQuickPhrases();
        }
        active = true;
        lastToggleTime = System.currentTimeMillis();
        buffer.setLength(0);
        selRow = (quickPhrases.isEmpty()) ? 0 : -1;
        selCol = 0;
        quickScroll = 0;
        shift = false;
        symMode = false;
        System.out.println("[VK] >>> OPENED VIRTUAL KEYBOARD <<< active=" + active);
        forceRedraw();
    }

    public static void close() {
        active = false;
        startHeld = false;
        selectHeld = false;
        System.out.println("[VK] >>> CLOSED VIRTUAL KEYBOARD <<< active=" + active);
        forceRedraw();
    }

    public static void forceRedraw() {
        try {
            if (Mobile.getPlatform() != null && Mobile.getPlatform().painter != null) {
                Mobile.getPlatform().painter.run();
            }
        } catch (Exception ignored) {}
    }

    /**
     * Intercept key events from SDL / MobilePlatform.
     * Return true if the key was consumed by VirtualKeyboard.
     */
    public static boolean isHotkey(int key) {
        // sdl_interface sends SDLK_F1 (0x4000003A / 1073741882) when START is held and Y is pressed.
        // Also support F2 (0x4000003B / 1073741883) and console F-keys.
        return key == 1073741882 || key == 0x4000003A || key == 58
            || key == 1073741883 || key == 0x4000003B || key == 59 || key == 60;
    }

    public static boolean isStartKey(int key) {
        // Only actual START / '#' keys (ASCII 35 = '#', SDL scancode 1073741900)
        return key == 35 || key == '#' || key == 1073741900;
    }

    public static boolean isSelectKey(int key) {
        // Only actual SELECT / '*' keys (ASCII 42 = '*', SDL scancode 1073741901)
        return key == 42 || key == '*' || key == 1073741901;
    }

    private static volatile boolean injecting = false;

    public static boolean handleKey(int key, boolean pressed) {
        if (injecting) {
            return false;
        }

        // 1. Hardware Hotkey: START + Y handled by sdl_interface emitting SDLK_F1 (0x4000003A)
        if (isHotkey(key)) {
            if (pressed && (System.currentTimeMillis() - lastToggleTime > 250)) {
                lastToggleTime = System.currentTimeMillis();
                System.out.println("[VK] >>> HOTKEY F1 (START + Y) DETECTED! Toggling Virtual Keyboard <<<");
                toggle();
            }
            return true;
        }

        // 2. Track SELECT and START states for SELECT + START combo
        if (isSelectKey(key)) {
            selectHeld = pressed;
            if (pressed && startHeld && (System.currentTimeMillis() - lastToggleTime > 250)) {
                lastToggleTime = System.currentTimeMillis();
                System.out.println("[VK] >>> SELECT + START COMBO DETECTED! Toggling Virtual Keyboard <<<");
                toggle();
                return true;
            }
            if (active) {
                if (pressed && (System.currentTimeMillis() - lastToggleTime > 250)) {
                    lastToggleTime = System.currentTimeMillis();
                    close();
                }
                return true;
            }
            return false;
        }

        if (isStartKey(key)) {
            startHeld = pressed;
            if (pressed && selectHeld && (System.currentTimeMillis() - lastToggleTime > 250)) {
                lastToggleTime = System.currentTimeMillis();
                System.out.println("[VK] >>> START + SELECT COMBO DETECTED! Toggling Virtual Keyboard <<<");
                toggle();
                return true;
            }
            if (active) {
                if (pressed) {
                    submitAndClose();
                }
                return true;
            }
            return false;
        }

        // If not active, pass all game keys (D-pad, 0-9, 1-3-7-9 skills, A, B, X, Y) cleanly to game
        if (!active) {
            return false;
        }

        // When active: consume all inputs so game character does not move or cast skills
        if (pressed) {
            processActiveInput(key);
            forceRedraw();
        }
        return true;
    }

    private static void processActiveInput(int key) {
        // D-pad Up
        if (key == -1 || key == 50 || key == 1073741906 || key == '2') {
            moveUp();
        }
        // D-pad Down
        else if (key == -2 || key == 56 || key == 1073741905 || key == '8') {
            moveDown();
        }
        // D-pad Left
        else if (key == -3 || key == 52 || key == 1073741904 || key == '4') {
            moveLeft();
        }
        // D-pad Right
        else if (key == -4 || key == 54 || key == 1073741903 || key == '6') {
            moveRight();
        }
        // Button A or X (Confirm / Type / Select):
        // Physical button A sends 119 ('w'). Button X sends 13 (Enter) or 53 ('5').
        else if (key == 119 || key == 'w' || key == 'W' || key == 13 || key == 111 || key == -5 || key == -7 || key == 'x' || key == 'X' || key == 10 || key == 32 || key == 53 || key == '5') {
            pressCurrentKey();
        }
        // Button B (Backspace / Close when empty):
        // Physical button B sends 48 ('0').
        else if (key == 48 || key == '0' || key == 8 || key == 127 || key == 27) {
            doBackspace();
        }
        // Button Y (Space):
        // Physical button Y sends 113 ('q').
        else if (key == -6 || key == 113 || key == 'q' || key == 'Q' || key == 'y' || key == 'Y') {
            doSpace();
        }
        // Shoulder buttons L1 / R1: Quick cycle shift modes (abc -> ABC -> 123 -> sym)
        else if (key == 49 || key == '1' || key == 51 || key == '3' || key == 1073741907 || key == 1073741908) {
            toggleShift();
        }
        // Button START: Submit and close
        else if (isStartKey(key)) {
            submitAndClose();
        }
        // Button SELECT: Close
        else if (isSelectKey(key)) {
            if (System.currentTimeMillis() - lastToggleTime > 250) {
                close();
            }
        }
    }

    private static void moveUp() {
        if (selRow > -1) {
            selRow--;
            if (selRow == -1 && quickPhrases.isEmpty()) {
                selRow = 0;
            }
        }
        clampCol();
    }

    private static void moveDown() {
        if (selRow < 4) {
            selRow++;
        }
        clampCol();
    }

    private static void moveLeft() {
        if (selRow == -1) {
            if (selCol > 0) {
                selCol--;
            } else if (quickScroll > 0) {
                quickScroll--;
            }
        } else {
            if (selCol > 0) {
                selCol--;
            } else {
                selCol = getMaxCol(selRow) - 1;
            }
        }
    }

    private static void moveRight() {
        if (selRow == -1) {
            if (selCol + quickScroll < quickPhrases.size() - 1) {
                if (selCol < 3) {
                    selCol++;
                } else {
                    quickScroll++;
                }
            }
        } else {
            if (selCol < getMaxCol(selRow) - 1) {
                selCol++;
            } else {
                selCol = 0;
            }
        }
    }

    private static int getMaxCol(int row) {
        if (row == -1) return Math.min(quickPhrases.size(), 4);
        if (row >= 0 && row <= 3) return 10;
        if (row == 4) return ACTION_LABELS.length;
        return 1;
    }

    private static void clampCol() {
        int max = getMaxCol(selRow);
        if (selCol >= max) {
            selCol = max - 1;
        }
        if (selCol < 0) selCol = 0;
    }

    private static void pressCurrentKey() {
        if (selRow == -1) {
            // Selecting from Quick Bar: Immediately inject and close!
            int idx = quickScroll + selCol;
            if (idx >= 0 && idx < quickPhrases.size()) {
                String chosen = quickPhrases.get(idx);
                close();
                inject(chosen);
            }
            return;
        }

        if (selRow >= 0 && selRow <= 3) {
            String[][] layout = symMode ? ROWS_SYM : (shift ? ROWS_UPPER : ROWS_LOWER);
            if (selCol >= 0 && selCol < layout[selRow].length) {
                buffer.append(layout[selRow][selCol]);
                // Single-char shift behaves like phone keyboard
                if (shift && !symMode) {
                    shift = false;
                }
            }
            return;
        }

        if (selRow == 4) {
            switch (selCol) {
                case 0: toggleShift(); break;
                case 1: doSpace(); break;
                case 2: doBackspace(); break;
                case 3: submitAndClose(); break;
                case 4: close(); break;
            }
        }
    }

    private static void doBackspace() {
        if (buffer.length() > 0) {
            buffer.deleteCharAt(buffer.length() - 1);
        } else {
            close();
        }
    }

    private static void doSpace() {
        buffer.append(' ');
    }

    private static void toggleShift() {
        if (!shift && !symMode) {
            shift = true;
        } else if (shift && !symMode) {
            shift = false;
            symMode = true;
        } else {
            symMode = false;
            shift = false;
        }
    }

    private static void submitAndClose() {
        String text = buffer.toString();
        close();
        if (!text.isEmpty()) {
            inject(text);
        }
    }

    /**
     * Inject string into active game input field.
     */
    public static void inject(final String text) {
        if (text == null || text.isEmpty()) return;

        // 1. Direct LCDUI TextBox support
        try {
            if (Mobile.getDisplay() != null) {
                Displayable cur = Mobile.getDisplay().getCurrent();
                if (cur instanceof TextBox) {
                    ((TextBox) cur).setString(text);
                    return;
                }
            }
        } catch (Exception ignored) {}

        // 2. Keystroke injection for Canvas-based Online Games
        new Thread(() -> {
            try {
                injecting = true;
                Thread.sleep(80);
                for (int i = 0; i < text.length(); i++) {
                    char c = text.charAt(i);
                    Mobile.getPlatform().keyPressed((int) c);
                    Thread.sleep(20);
                    Mobile.getPlatform().keyReleased((int) c);
                    Thread.sleep(20);
                }
            } catch (Exception ignored) {
            } finally {
                injecting = false;
            }
        }).start();
    }

    /**
     * Render the virtual keyboard on top of the given game LCD canvas.
     */
    public static void renderIfActive(BufferedImage canvas) {
        if (!active || canvas == null) return;

        Graphics2D g = (Graphics2D) canvas.getGraphics();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

        int W = canvas.getWidth();
        int H = canvas.getHeight();

        Font baseFont = (customFont != null) ? customFont : new Font(Font.SANS_SERIF, Font.PLAIN, 12);
        Font fontKey = baseFont.deriveFont(Font.BOLD, (W >= 300) ? 12f : 10f);
        Font fontText = baseFont.deriveFont(Font.PLAIN, (W >= 300) ? 13f : 11f);
        Font fontSmall = baseFont.deriveFont(Font.PLAIN, 9f);

        // Keyboard Panel Dimensions (docked to bottom)
        int panelH = (H >= 300) ? 190 : 162;
        int panelY = H - panelH - 2;
        int panelX = 4;
        int panelW = W - 8;

        // Background Panel
        g.setColor(BG_OVERLAY);
        g.fillRoundRect(panelX, panelY, panelW, panelH, 10, 10);
        g.setColor(BORDER_BOX);
        g.drawRoundRect(panelX, panelY, panelW, panelH, 10, 10);

        int curY = panelY + 6;

        // 1. Text Preview Box
        int previewH = 22;
        int previewW = panelW - 12;
        int previewX = panelX + 6;
        g.setColor(PREVIEW_BG);
        g.fillRoundRect(previewX, curY, previewW, previewH, 6, 6);
        g.setColor(BORDER_BOX);
        g.drawRoundRect(previewX, curY, previewW, previewH, 6, 6);

        // Preview text with cursor
        g.setFont(fontText);
        g.setColor(Color.WHITE);
        String displayText = buffer.toString();

        long now = System.currentTimeMillis();
        if (now - cursorBlinkTime > 500) {
            cursorVisible = !cursorVisible;
            cursorBlinkTime = now;
        }

        FontMetrics fmText = g.getFontMetrics();
        int textW = fmText.stringWidth(displayText);
        int textX = previewX + 8;
        int textY = curY + 15;

        // Scroll preview text if too long
        if (textW > previewW - 20) {
            textX = previewX + previewW - textW - 14;
        }
        g.drawString(displayText, textX, textY);

        if (cursorVisible) {
            g.setColor(ACCENT_COLOR);
            int cursorX = textX + textW + 1;
            g.fillRect(cursorX, curY + 4, 2, 14);
        }

        curY += previewH + 4;

        // 2. Quick Phrases Bar (Row -1)
        if (!quickPhrases.isEmpty()) {
            int qh = 18;
            int qx = panelX + 6;
            int qw = (panelW - 12);
            int pillCount = Math.min(quickPhrases.size() - quickScroll, 4);
            int pillW = (qw - ((pillCount - 1) * 4)) / Math.max(1, pillCount);

            g.setFont(fontSmall);
            FontMetrics fmSmall = g.getFontMetrics();

            for (int i = 0; i < pillCount; i++) {
                int itemIdx = quickScroll + i;
                if (itemIdx >= quickPhrases.size()) break;

                int px = qx + i * (pillW + 4);
                boolean isSelected = (selRow == -1 && selCol == i);

                if (isSelected) {
                    g.setColor(ACCENT_COLOR);
                    g.fillRoundRect(px, curY, pillW, qh, 6, 6);
                    g.setColor(Color.BLACK);
                } else {
                    g.setColor(KEY_BG);
                    g.fillRoundRect(px, curY, pillW, qh, 6, 6);
                    g.setColor(MUTED_TEXT);
                    g.drawRoundRect(px, curY, pillW, qh, 6, 6);
                    g.setColor(KEY_TEXT);
                }

                String phrase = quickPhrases.get(itemIdx);
                // Truncate if pill too small
                if (fmSmall.stringWidth(phrase) > pillW - 6) {
                    while (phrase.length() > 2 && fmSmall.stringWidth(phrase + "..") > pillW - 6) {
                        phrase = phrase.substring(0, phrase.length() - 1);
                    }
                    phrase += "..";
                }

                int strX = px + (pillW - fmSmall.stringWidth(phrase)) / 2;
                g.drawString(phrase, strX, curY + 13);
            }
            curY += qh + 4;
        }

        // 3. Keyboard Grid (Rows 0 to 3)
        String[][] layout = symMode ? ROWS_SYM : (shift ? ROWS_UPPER : ROWS_LOWER);
        int keyRowH = 18;
        int gridX = panelX + 6;
        int gridW = panelW - 12;
        int keyW = (gridW - (9 * 2)) / 10;

        g.setFont(fontKey);
        FontMetrics fmKey = g.getFontMetrics();

        for (int r = 0; r < 4; r++) {
            for (int c = 0; c < 10; c++) {
                int kx = gridX + c * (keyW + 2);
                int ky = curY + r * (keyRowH + 2);
                boolean isSelected = (selRow == r && selCol == c);

                if (isSelected) {
                    g.setColor(ACCENT_COLOR);
                    g.fillRoundRect(kx, ky, keyW, keyRowH, 4, 4);
                    g.setColor(Color.BLACK);
                } else {
                    g.setColor(KEY_BG);
                    g.fillRoundRect(kx, ky, keyW, keyRowH, 4, 4);
                    g.setColor(KEY_TEXT);
                }

                String kStr = layout[r][c];
                int kw = fmKey.stringWidth(kStr);
                g.drawString(kStr, kx + (keyW - kw) / 2, ky + 13);
            }
        }

        curY += (keyRowH + 2) * 4 + 2;

        // 4. Action Row (Row 4)
        int actW = (gridW - ((ACTION_LABELS.length - 1) * 3)) / ACTION_LABELS.length;
        g.setFont(fontSmall);
        FontMetrics fmAct = g.getFontMetrics();

        for (int i = 0; i < ACTION_LABELS.length; i++) {
            int ax = gridX + i * (actW + 3);
            boolean isSelected = (selRow == 4 && selCol == i);

            if (isSelected) {
                g.setColor(ACCENT_COLOR);
                g.fillRoundRect(ax, curY, actW, keyRowH, 4, 4);
                g.setColor(Color.BLACK);
            } else {
                g.setColor((i == 3) ? ACCENT_DIM : KEY_BG);
                g.fillRoundRect(ax, curY, actW, keyRowH, 4, 4);
                g.setColor(Color.WHITE);
            }

            String lbl = ACTION_LABELS[i];
            if (i == 0) {
                lbl = symMode ? "abc" : (shift ? "123" : "Shift");
            }
            int lw = fmAct.stringWidth(lbl);
            g.drawString(lbl, ax + (actW - lw) / 2, curY + 12);
        }

        curY += keyRowH + 3;

        // 5. Footer Help Hint
        g.setFont(fontSmall);
        g.setColor(MUTED_TEXT);
        String hint = "A/X:Gõ  B:Xóa  Y:Cách  START:Xong  SELECT:Đóng  [START+Y]";
        int hintW = g.getFontMetrics().stringWidth(hint);
        g.drawString(hint, panelX + (panelW - hintW) / 2, curY + 8);

        g.dispose();
    }
}
