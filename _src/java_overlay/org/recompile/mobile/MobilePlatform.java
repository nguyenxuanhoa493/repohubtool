package org.recompile.mobile;

import java.awt.image.BufferedImage;
import java.net.URL;
import javax.microedition.lcdui.Display;
import javax.microedition.lcdui.Displayable;
import javax.microedition.lcdui.Image;
import org.recompile.freej2me.VirtualKeyboard;

public class MobilePlatform {
    private PlatformImage lcd;
    private PlatformGraphics gc;
    public int lcdWidth;
    public int lcdHeight;
    public MIDletLoader loader;
    public Runnable painter;
    public String dataPath = "";
    public String rootPath = "";
    private int keyState = 0;
    private int[] keyStateArr = new int[6];
    private int s = 0;
    private int e = 0;
    public boolean suppressKeyEvents = false;

    public MobilePlatform(int width, int height) {
        this.lcdWidth = width;
        this.lcdHeight = height;
        this.lcd = new PlatformImage(width, height);
        this.gc = this.lcd.getGraphics();
        this.painter = new MobilePlatform$1(this);
    }

    public void push(int val) {
        if ((this.e + 1) % 6 == this.s) {
            return;
        }
        this.keyStateArr[this.e] = val;
        this.e = (this.e + 1) % 6;
    }

    public int pop() {
        if (this.s == this.e) {
            return 0;
        }
        int val = this.keyStateArr[this.s];
        this.s = (this.s + 1) % 6;
        return val;
    }

    public void resizeLCD(int width, int height) {
        this.lcdWidth = width;
        this.lcdHeight = height;
        this.lcd = new PlatformImage(width, height);
        this.gc = this.lcd.getGraphics();
    }

    public BufferedImage getLCD() {
        BufferedImage img = this.lcd.getCanvas();
        VirtualKeyboard.renderIfActive(img);
        return img;
    }

    public void setPainter(Runnable painter) {
        this.painter = painter;
    }

    public void keyPressed(int key) {
        if (VirtualKeyboard.handleKey(key, true)) {
            return;
        }
        this.updateKeyState(key, 1);
        if (!this.suppressKeyEvents) {
            Display display = Mobile.getDisplay();
            if (display != null) {
                Displayable cur = display.getCurrent();
                if (cur != null) {
                    cur.keyPressed(key);
                }
            }
        }
    }

    public void keyReleased(int key) {
        if (VirtualKeyboard.handleKey(key, false)) {
            return;
        }
        this.updateKeyState(key, 0);
        if (!this.suppressKeyEvents) {
            Display display = Mobile.getDisplay();
            if (display != null) {
                Displayable cur = display.getCurrent();
                if (cur != null) {
                    cur.keyReleased(key);
                }
            }
        }
    }

    public void keyRepeated(int key) {
        if (VirtualKeyboard.active) {
            return;
        }
        if (!this.suppressKeyEvents) {
            Display display = Mobile.getDisplay();
            if (display != null) {
                Displayable cur = display.getCurrent();
                if (cur != null) {
                    cur.keyRepeated(key);
                }
            }
        }
    }

    public void pointerDragged(int x, int y) {
        if (VirtualKeyboard.active) return;
        Display display = Mobile.getDisplay();
        if (display != null) {
            Displayable cur = display.getCurrent();
            if (cur != null) {
                cur.pointerDragged(x, y);
            }
        }
    }

    public void pointerPressed(int x, int y) {
        if (VirtualKeyboard.active) return;
        Display display = Mobile.getDisplay();
        if (display != null) {
            Displayable cur = display.getCurrent();
            if (cur != null) {
                cur.pointerPressed(x, y);
            }
        }
    }

    public void pointerReleased(int x, int y) {
        if (VirtualKeyboard.active) return;
        Display display = Mobile.getDisplay();
        if (display != null) {
            Displayable cur = display.getCurrent();
            if (cur != null) {
                cur.pointerReleased(x, y);
            }
        }
    }

    public synchronized int getKeyState() {
        return this.keyState;
    }

    private void updateKeyState(int key, int state) {
        int mask = 0;
        switch (key) {
            case 50: case -1: mask = 2; break;
            case 52: case -3: mask = 4; break;
            case 54: case -4: mask = 32; break;
            case 56: case -2: mask = 64; break;
            case 53: case -5: mask = 256; break;
            case 55: mask = 512; break;
            case 57: mask = 1024; break;
            case 42: mask = 2048; break;
            case 35: mask = 4096; break;
            default: return;
        }
        synchronized (this) {
            if (state == 1) {
                this.keyState |= mask;
            } else {
                this.keyState &= ~mask;
            }
        }
    }

    private int convertGameKeyCode(int key) {
        switch (key) {
            case 50: case -1: return 2;
            case 52: case -3: return 4;
            case 54: case -4: return 32;
            case 56: case -2: return 64;
            case 53: case -5: return 256;
            case 55: return 512;
            case 57: return 1024;
            case 42: return 2048;
            case 35: return 4096;
            default: return 0;
        }
    }

    public boolean loadJar(String jarPath) {
        try {
            URL url;
            if (jarPath.startsWith("/")) {
                url = new URL("file:" + jarPath);
            } else {
                url = new URL(jarPath);
            }
            System.out.println("Jar URL: " + url);
            String title = "";
            String[] parts = jarPath.split("/");
            if (parts.length > 0 && parts[parts.length - 1].endsWith(".jar")) {
                String filename = parts[parts.length - 1];
                title = filename.substring(0, filename.length() - 4);
                System.out.println("Jar Title: " + title);
            }
            this.loader = new MIDletLoader(new URL[]{url}, jarPath, title + " " + this.lcdWidth + " " + this.lcdHeight);
            return true;
        } catch (Exception e) {
            System.out.println(e.getMessage());
            e.printStackTrace();
            return false;
        }
    }

    public void runJar() {
        try {
            this.loader.start();
        } catch (Exception e) {
            System.out.println("Error Running Jar");
            e.printStackTrace();
        }
    }

    public void flushGraphics(Image img, int x, int y, int w, int h) {
        this.gc.flushGraphics(img, x, y, w, h);
        if (this.painter != null) {
            this.painter.run();
        }
    }

    public void repaint(Image img, int x, int y, int w, int h) {
        this.gc.flushGraphics(img, x, y, w, h);
        if (this.painter != null) {
            this.painter.run();
        }
    }
}
