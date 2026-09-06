package org.recompile.freej2me;

import java.awt.Font;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.util.Timer;
import java.util.TimerTask;
import org.lwjgl.system.macosx.CoreGraphics;
import org.recompile.mobile.Audio;
import org.recompile.mobile.Mobile;
import org.recompile.mobile.MobilePlatform;

/* JADX INFO: loaded from: freej2me-sdl.jar:org/recompile/freej2me/Anbu.class */
public class Anbu {
    private final SDL sdl;
    private final int lcdWidth;
    private final int lcdHeight;
    private final int[] frameArgb;
    private final byte[] frameBgra;
    private final Runnable painter;
    private int soundLevel;
    private final SDLConfig config;
    private static Font globalFont = null;
    private final byte[] keyPix;
    private final boolean[] pressedKeys = new boolean[128];
    private long pretime = 0;
    private int useFlag = 0;
    private int fps = 16;
    private int showfps = 0;

    public static void main(String[] strArr) {
        System.loadLibrary("audio");
        new Anbu(strArr);
    }

    static void convertArgbToBgra(int[] iArr, byte[] bArr) {
        if (bArr.length < iArr.length * 4) {
            throw new IllegalArgumentException("ARGB8888 frame buffer is too small");
        }
        for (int i = 0; i < iArr.length; i++) {
            int i2 = iArr[i];
            int i3 = i * 4;
            bArr[i3] = (byte) i2;
            bArr[i3 + 1] = (byte) (i2 >>> 8);
            bArr[i3 + 2] = (byte) (i2 >>> 16);
            bArr[i3 + 3] = (byte) (i2 >>> 24);
        }
    }

    public static Font getFont() {
        if (globalFont != null) {
            return globalFont;
        }
        try {
            globalFont = Font.createFont(0, new File("./font.ttf")).deriveFont(0, 12.0f);
        } catch (Exception e) {
            System.err.println("字体文件加载失败,使用默认字体: " + e.getMessage());
            globalFont = new Font("MiSans Normal", 0, 12);
        }
        return globalFont;
    }

    public Anbu(String[] strArr) {
        this.soundLevel = 100;
        byte[] bArr = new byte[720];
        bArr[13] = 1;
        bArr[14] = 1;
        bArr[15] = 1;
        bArr[16] = 1;
        bArr[17] = 1;
        bArr[18] = 1;
        bArr[19] = 1;
        bArr[20] = 1;
        bArr[21] = 1;
        bArr[22] = 1;
        bArr[25] = 1;
        bArr[26] = 1;
        bArr[27] = 1;
        bArr[28] = 1;
        bArr[29] = 1;
        bArr[30] = 1;
        bArr[31] = 1;
        bArr[32] = 1;
        bArr[33] = 1;
        bArr[34] = 1;
        bArr[37] = 1;
        bArr[38] = 1;
        bArr[45] = 1;
        bArr[46] = 1;
        bArr[49] = 1;
        bArr[50] = 1;
        bArr[57] = 1;
        bArr[58] = 1;
        bArr[61] = 1;
        bArr[62] = 1;
        bArr[69] = 1;
        bArr[70] = 1;
        bArr[73] = 1;
        bArr[74] = 1;
        bArr[75] = 1;
        bArr[76] = 1;
        bArr[77] = 1;
        bArr[78] = 1;
        bArr[79] = 1;
        bArr[80] = 1;
        bArr[81] = 1;
        bArr[82] = 1;
        bArr[85] = 1;
        bArr[86] = 1;
        bArr[87] = 1;
        bArr[88] = 1;
        bArr[89] = 1;
        bArr[90] = 1;
        bArr[91] = 1;
        bArr[92] = 1;
        bArr[93] = 1;
        bArr[94] = 1;
        bArr[97] = 1;
        bArr[98] = 1;
        bArr[109] = 1;
        bArr[110] = 1;
        bArr[121] = 1;
        bArr[122] = 1;
        bArr[157] = 1;
        bArr[158] = 1;
        bArr[165] = 1;
        bArr[166] = 1;
        bArr[169] = 1;
        bArr[170] = 1;
        bArr[171] = 1;
        bArr[177] = 1;
        bArr[178] = 1;
        bArr[181] = 1;
        bArr[182] = 1;
        bArr[183] = 1;
        bArr[184] = 1;
        bArr[189] = 1;
        bArr[190] = 1;
        bArr[193] = 1;
        bArr[194] = 1;
        bArr[196] = 1;
        bArr[197] = 1;
        bArr[201] = 1;
        bArr[202] = 1;
        bArr[205] = 1;
        bArr[206] = 1;
        bArr[209] = 1;
        bArr[210] = 1;
        bArr[213] = 1;
        bArr[214] = 1;
        bArr[217] = 1;
        bArr[218] = 1;
        bArr[222] = 1;
        bArr[223] = 1;
        bArr[225] = 1;
        bArr[226] = 1;
        bArr[229] = 1;
        bArr[230] = 1;
        bArr[235] = 1;
        bArr[236] = 1;
        bArr[237] = 1;
        bArr[238] = 1;
        bArr[241] = 1;
        bArr[242] = 1;
        bArr[248] = 1;
        bArr[249] = 1;
        bArr[250] = 1;
        bArr[253] = 1;
        bArr[254] = 1;
        bArr[261] = 1;
        bArr[262] = 1;
        bArr[265] = 1;
        bArr[266] = 1;
        bArr[273] = 1;
        bArr[274] = 1;
        bArr[301] = 1;
        bArr[302] = 1;
        bArr[303] = 1;
        bArr[304] = 1;
        bArr[305] = 1;
        bArr[306] = 1;
        bArr[307] = 1;
        bArr[308] = 1;
        bArr[309] = 1;
        bArr[310] = 1;
        bArr[313] = 1;
        bArr[314] = 1;
        bArr[315] = 1;
        bArr[316] = 1;
        bArr[317] = 1;
        bArr[318] = 1;
        bArr[319] = 1;
        bArr[320] = 1;
        bArr[321] = 1;
        bArr[322] = 1;
        bArr[325] = 1;
        bArr[326] = 1;
        bArr[337] = 1;
        bArr[338] = 1;
        bArr[349] = 1;
        bArr[350] = 1;
        bArr[351] = 1;
        bArr[352] = 1;
        bArr[353] = 1;
        bArr[354] = 1;
        bArr[355] = 1;
        bArr[356] = 1;
        bArr[357] = 1;
        bArr[358] = 1;
        bArr[361] = 1;
        bArr[362] = 1;
        bArr[363] = 1;
        bArr[364] = 1;
        bArr[365] = 1;
        bArr[366] = 1;
        bArr[367] = 1;
        bArr[368] = 1;
        bArr[369] = 1;
        bArr[370] = 1;
        bArr[373] = 1;
        bArr[374] = 1;
        bArr[385] = 1;
        bArr[386] = 1;
        bArr[397] = 1;
        bArr[398] = 1;
        bArr[399] = 1;
        bArr[400] = 1;
        bArr[401] = 1;
        bArr[402] = 1;
        bArr[403] = 1;
        bArr[404] = 1;
        bArr[405] = 1;
        bArr[406] = 1;
        bArr[409] = 1;
        bArr[410] = 1;
        bArr[411] = 1;
        bArr[412] = 1;
        bArr[413] = 1;
        bArr[414] = 1;
        bArr[415] = 1;
        bArr[416] = 1;
        bArr[417] = 1;
        bArr[418] = 1;
        bArr[445] = 1;
        bArr[446] = 1;
        bArr[447] = 1;
        bArr[448] = 1;
        bArr[449] = 1;
        bArr[450] = 1;
        bArr[451] = 1;
        bArr[452] = 1;
        bArr[453] = 1;
        bArr[454] = 1;
        bArr[457] = 1;
        bArr[458] = 1;
        bArr[459] = 1;
        bArr[460] = 1;
        bArr[461] = 1;
        bArr[462] = 1;
        bArr[463] = 1;
        bArr[464] = 1;
        bArr[465] = 1;
        bArr[466] = 1;
        bArr[469] = 1;
        bArr[470] = 1;
        bArr[481] = 1;
        bArr[482] = 1;
        bArr[495] = 1;
        bArr[496] = 1;
        bArr[497] = 1;
        bArr[498] = 1;
        bArr[499] = 1;
        bArr[500] = 1;
        bArr[501] = 1;
        bArr[507] = 1;
        bArr[508] = 1;
        bArr[509] = 1;
        bArr[510] = 1;
        bArr[511] = 1;
        bArr[512] = 1;
        bArr[513] = 1;
        bArr[525] = 1;
        bArr[526] = 1;
        bArr[537] = 1;
        bArr[538] = 1;
        bArr[541] = 1;
        bArr[542] = 1;
        bArr[543] = 1;
        bArr[544] = 1;
        bArr[545] = 1;
        bArr[546] = 1;
        bArr[547] = 1;
        bArr[548] = 1;
        bArr[549] = 1;
        bArr[550] = 1;
        bArr[553] = 1;
        bArr[554] = 1;
        bArr[555] = 1;
        bArr[556] = 1;
        bArr[557] = 1;
        bArr[558] = 1;
        bArr[559] = 1;
        bArr[560] = 1;
        bArr[561] = 1;
        bArr[562] = 1;
        bArr[589] = 1;
        bArr[590] = 1;
        bArr[591] = 1;
        bArr[592] = 1;
        bArr[593] = 1;
        bArr[594] = 1;
        bArr[595] = 1;
        bArr[596] = 1;
        bArr[597] = 1;
        bArr[598] = 1;
        bArr[601] = 1;
        bArr[602] = 1;
        bArr[603] = 1;
        bArr[604] = 1;
        bArr[605] = 1;
        bArr[606] = 1;
        bArr[607] = 1;
        bArr[608] = 1;
        bArr[609] = 1;
        bArr[610] = 1;
        bArr[613] = 1;
        bArr[614] = 1;
        bArr[617] = 1;
        bArr[618] = 1;
        bArr[621] = 1;
        bArr[622] = 1;
        bArr[625] = 1;
        bArr[626] = 1;
        bArr[629] = 1;
        bArr[630] = 1;
        bArr[633] = 1;
        bArr[634] = 1;
        bArr[637] = 1;
        bArr[638] = 1;
        bArr[641] = 1;
        bArr[642] = 1;
        bArr[645] = 1;
        bArr[646] = 1;
        bArr[649] = 1;
        bArr[650] = 1;
        bArr[653] = 1;
        bArr[654] = 1;
        bArr[657] = 1;
        bArr[658] = 1;
        bArr[661] = 1;
        bArr[662] = 1;
        bArr[665] = 1;
        bArr[666] = 1;
        bArr[669] = 1;
        bArr[670] = 1;
        bArr[673] = 1;
        bArr[674] = 1;
        bArr[677] = 1;
        bArr[678] = 1;
        bArr[681] = 1;
        bArr[682] = 1;
        bArr[685] = 1;
        bArr[686] = 1;
        bArr[689] = 1;
        bArr[690] = 1;
        bArr[693] = 1;
        bArr[694] = 1;
        bArr[697] = 1;
        bArr[698] = 1;
        bArr[701] = 1;
        bArr[702] = 1;
        bArr[705] = 1;
        bArr[706] = 1;
        this.keyPix = bArr;
        this.sdl = new SDL(this, null);
        if (strArr.length < 3) {
            System.out.println("参数数量不一致");
            System.exit(0);
        }
        this.lcdWidth = Integer.parseInt(strArr[1]);
        this.lcdHeight = Integer.parseInt(strArr[2]);
        this.frameArgb = new int[this.lcdWidth * this.lcdHeight];
        this.frameBgra = new byte[this.lcdWidth * this.lcdHeight * 4];
        String strSubstring = "";
        String[] strArrSplit = strArr[0].split("/");
        if (strArrSplit.length > 0 && strArrSplit[strArrSplit.length - 1].endsWith(".jar")) {
            strSubstring = strArrSplit[strArrSplit.length - 1].substring(0, strArrSplit[strArrSplit.length - 1].length() - 4);
            System.out.println("jar file name:" + strSubstring);
        }
        Mobile.setPlatform(new MobilePlatform(this.lcdWidth, this.lcdHeight));
        Mobile.getPlatform().dataPath = "./";
        Mobile.getPlatform().rootPath = "/storage/roms/j2me/";
        this.soundLevel = Integer.parseInt(strArr[3]);
        Audio.setVol(this.soundLevel);
        this.config = new SDLConfig();
        this.config.init(String.valueOf(strSubstring) + this.lcdWidth + this.lcdHeight);
        settingsChanged();
        this.painter = new Runnable() { // from class: org.recompile.freej2me.Anbu.1
            @Override // java.lang.Runnable
            public void run() {
                try {
                    long jCurrentTimeMillis = (((long) Anbu.this.fps) - System.currentTimeMillis()) - Anbu.this.pretime;
                    if (jCurrentTimeMillis > 0) {
                        Thread.sleep(jCurrentTimeMillis);
                    }
                    Anbu.this.pretime = System.currentTimeMillis();
                    Mobile.getPlatform().getLCD().getRGB(0, 0, Anbu.this.lcdWidth, Anbu.this.lcdHeight, Anbu.this.frameArgb, 0, Anbu.this.lcdWidth);
                    Anbu.convertArgbToBgra(Anbu.this.frameArgb, Anbu.this.frameBgra);
                    if (Anbu.this.showfps < 60) {
                        int i = Anbu.this.useFlag * 144;
                        for (int i2 = 0; i2 < 12; i2++) {
                            for (int i3 = 0; i3 < 12; i3++) {
                                int i4 = (((10 + i2) * Anbu.this.lcdWidth) + 10 + i3) * 4;
                                switch (Anbu.this.keyPix[i + (i2 * 12) + i3]) {
                                    case 0:
                                        Anbu.this.frameBgra[i4] = 0;
                                        Anbu.this.frameBgra[i4 + 1] = 0;
                                        Anbu.this.frameBgra[i4 + 2] = 0;
                                        Anbu.this.frameBgra[i4 + 3] = -1;
                                        break;
                                    case 1:
                                        Anbu.this.frameBgra[i4] = -64;
                                        Anbu.this.frameBgra[i4 + 1] = -1;
                                        Anbu.this.frameBgra[i4 + 2] = 0;
                                        Anbu.this.frameBgra[i4 + 3] = -1;
                                        break;
                                }
                            }
                        }
                        Anbu.this.showfps++;
                    }
                    Anbu.this.sdl.frame.write(Anbu.this.frameBgra);
                    Anbu.this.sdl.frame.flush();
                } catch (Exception e) {
                    System.out.println("Failed to write sdl_interface");
                    System.out.println(e.getMessage());
                    new Thread(new Runnable() { // from class: org.recompile.freej2me.Anbu.1.1
                        @Override // java.lang.Runnable
                        public void run() {
                            try {
                                Thread.sleep(2000L);
                            } catch (InterruptedException e2) {
                                e2.printStackTrace();
                            }
                            System.exit(0);
                        }
                    }).start();
                    Audio.destroy();
                    Mobile.destroy();
                    Anbu.this.sdl.stop();
                    System.exit(0);
                }
            }
        };
        Mobile.getPlatform().setPainter(this.painter);
        System.out.println("jar文件:" + strArr[0]);
        if (Mobile.getPlatform().loadJar(strArr[0])) {
            this.sdl.start();
            Mobile.getPlatform().runJar();
        } else {
            System.out.println("Couldn't load jar...");
            System.exit(0);
        }
    }

    private void settingsChanged() {
        this.fps = Integer.parseInt(this.config.settings.get("fps"));
        if (this.fps > 0) {
            this.fps = CoreGraphics.kCGErrorFailure / this.fps;
        }
        String str = this.config.settings.get("phone");
        this.useFlag = 0;
        if (!str.equals("n")) {
            if (!str.equals("e")) {
                if (!str.equals("s")) {
                    if (str.equals("m")) {
                        this.useFlag = 4;
                        return;
                    }
                    return;
                }
                this.useFlag = 3;
                return;
            }
            this.useFlag = 2;
            return;
        }
        this.useFlag = 1;
    }

    /* JADX INFO: loaded from: freej2me-sdl.jar:org/recompile/freej2me/Anbu$SDL.class */
    private class SDL {
        private Timer keytimer;
        private TimerTask keytask;
        private Process proc;
        private InputStream keys;
        public OutputStream frame;

        private SDL() {
        }

        /* synthetic */ SDL(Anbu anbu, SDL sdl) {
            this();
        }

        public void start() {
            try {
                this.proc = new ProcessBuilder("./sdl_interface", String.valueOf(Anbu.this.lcdWidth), String.valueOf(Anbu.this.lcdHeight)).redirectOutput(ProcessBuilder.Redirect.INHERIT).start();
                this.keys = this.proc.getErrorStream();
                BufferedReader bufferedReader = new BufferedReader(new InputStreamReader(this.keys));
                while (bufferedReader.ready() && bufferedReader.readLine() != null) {
                }
                this.frame = this.proc.getOutputStream();
                this.keytimer = new Timer();
                this.keytask = new SDLKeyTimerTask(this, null);
                this.keytimer.schedule(this.keytask, 0L, 5L);
            } catch (Exception e) {
                System.out.println("Failed to start sdl_interface");
                System.out.println(e.getMessage());
                System.exit(0);
            }
        }

        public void stop() {
            this.keytimer.cancel();
            this.proc.destroy();
        }

        /* JADX INFO: loaded from: freej2me-sdl.jar:org/recompile/freej2me/Anbu$SDL$SDLKeyTimerTask.class */
        private class SDLKeyTimerTask extends TimerTask {
            private int bin;
            private byte[] din;
            private int count;
            private int code;
            private int mobikey;
            private int mobikeyN;
            private int x;
            private int y;
            private boolean press;

            private SDLKeyTimerTask() {
                this.din = new byte[6];
                this.count = 0;
                this.code = 0;
                this.press = false;
            }

            /* synthetic */ SDLKeyTimerTask(SDL sdl, SDLKeyTimerTask sDLKeyTimerTask) {
                this();
            }

            @Override // java.util.TimerTask, java.lang.Runnable
            public void run() {
                while (true) {
                    try {
                        this.bin = SDL.this.keys.read();
                        if (this.bin == -1) {
                            return;
                        }
                        this.din[this.count] = (byte) (this.bin & 255);
                        this.count++;
                        if (this.count == 5) {
                            this.count = 0;
                            switch (this.din[0] >>> 4) {
                                case 0:
                                    this.code = ((this.din[1] & 255) << 24) | ((this.din[2] & 255) << 16) | ((this.din[3] & 255) << 8) | (this.din[4] & 255);
                                    boolean pressed = (this.din[0] % 2 != 0);
                                    if (VirtualKeyboard.handleKey(this.code, pressed)) {
                                        break;
                                    }
                                    this.mobikey = Anbu.this.getMobileKey(this.code);
                                    if (this.mobikey == 0) {
                                        break;
                                    }
                                    this.mobikeyN = (this.mobikey + 64) & 127;
                                    if (this.din[0] % 2 != 0) {
                                        if (!Anbu.this.pressedKeys[this.mobikeyN]) {
                                            Mobile.getPlatform().keyPressed(this.mobikey);
                                        } else {
                                            Mobile.getPlatform().keyRepeated(this.mobikey);
                                        }
                                        Anbu.this.pressedKeys[this.mobikeyN] = true;
                                    } else {
                                        Mobile.getPlatform().keyReleased(this.mobikey);
                                        Anbu.this.pressedKeys[this.mobikeyN] = false;
                                    }
                                    break;
                                case 1:
                                    this.x = ((this.din[1] << 8) & 65280) | (this.din[2] & 255);
                                    this.y = ((this.din[3] << 8) & 65280) | (this.din[4] & 255);
                                    if (this.din[0] % 2 == 0) {
                                        Mobile.getPlatform().pointerReleased(this.x, this.y);
                                        this.press = false;
                                        return;
                                    } else {
                                        if (this.press) {
                                            return;
                                        }
                                        Mobile.getPlatform().pointerPressed(this.x, this.y);
                                        this.press = true;
                                        return;
                                    }
                            }
                        }
                    } catch (Exception unused) {
                        return;
                    }
                }
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public int getMobileKey(int i) {
        switch (i) {
            case 1073741886:
                setPhoneMode(0);
                return 0;
            case 1073741887:
                setPhoneMode(1);
                return 0;
            case 1073741888:
                setPhoneMode(2);
                return 0;
            case 1073741889:
                setPhoneMode(3);
                return 0;
            case 1073741890:
                setPhoneMode(4);
                return 0;
            default:
                if (this.useFlag == 1) {
                    switch (i) {
                        case 13:
                        case 111:
                        case 0x4000003A: // Button X on TrimUI -> OK / FIRE
                            return -5;
                        case 1073741903:
                            return -4;
                        case 1073741904:
                            return -3;
                        case 1073741905:
                            return -2;
                        case 1073741906:
                            return -1;
                    }
                }
                if (this.useFlag == 2) {
                    switch (i) {
                        case 13:
                        case 111:
                        case 0x4000003A: // Button X on TrimUI -> OK / FIRE
                            return -5;
                        case 48:
                            return 109;
                        case 49:
                            return 114;
                        case 51:
                            return 121;
                        case 55:
                            return 118;
                        case 57:
                            return 110;
                        case 101:
                            return 117;
                        case 114:
                            return 106;
                        case 1073741903:
                            return -4;
                        case 1073741904:
                            return -3;
                        case 1073741905:
                            return -2;
                        case 1073741906:
                            return -1;
                    }
                }
                if (this.useFlag == 3) {
                    switch (i) {
                        case 13:
                        case 111:
                        case 0x4000003A: // Button X on TrimUI
                            return -26;
                        case 113:
                            return -1;
                        case 119:
                            return -4;
                        case 1073741903:
                            return -62;
                        case 1073741904:
                            return -61;
                        case 1073741905:
                            return -60;
                        case 1073741906:
                            return -59;
                    }
                }
                if (this.useFlag == 4) {
                    switch (i) {
                        case 13:
                        case 111:
                        case 0x4000003A: // Button X on TrimUI
                            return -20;
                        case 113:
                            return -21;
                        case 119:
                            return -22;
                        case 1073741903:
                            return -5;
                        case 1073741904:
                            return -2;
                        case 1073741905:
                            return -6;
                        case 1073741906:
                            return -1;
                    }
                }
                switch (i) {
                    case -1:
                        Audio.destroy();
                        Mobile.destroy();
                        this.sdl.stop();
                        System.exit(0);
                        return 0;
                    case 13:
                    case 0x4000003A: // Button X on TrimUI -> Key 5 / OK
                        return 53;
                    case 27:
                        Audio.destroy();
                        Mobile.destroy();
                        this.sdl.stop();
                        System.exit(0);
                        return 0;
                    case 35:
                        return 35;
                    case 42:
                        return 42;
                    case 48:
                        return 48;
                    case 49:
                        return 49;
                    case 50:
                        return 50;
                    case 51:
                        return 51;
                    case 52:
                        return 52;
                    case 53:
                        return 53;
                    case 54:
                        return 54;
                    case 55:
                        return 55;
                    case 56:
                        return 56;
                    case 57:
                        return 57;
                    case 99:
                        setPhoneMode((this.useFlag + 1) % 5);
                        return 0;
                    case 100:
                        if (this.soundLevel > 20) {
                            this.soundLevel -= 20;
                        } else {
                            this.soundLevel = 0;
                        }
                        Audio.setVol(this.soundLevel);
                        this.config.settings.put("sound", String.valueOf(this.soundLevel));
                        this.config.saveConfig();
                        return 0;
                    case 101:
                        return 42;
                    case 111:
                        return 53;
                    case 113:
                        return -6;
                    case 114:
                        return 35;
                    case 117:
                        if (this.soundLevel < 80) {
                            this.soundLevel += 20;
                        } else {
                            this.soundLevel = 100;
                        }
                        Audio.setVol(this.soundLevel);
                        this.config.settings.put("sound", String.valueOf(this.soundLevel));
                        this.config.saveConfig();
                        return 0;
                    case 119:
                        return -7;
                    case 1073741898:
                        Audio.destroy();
                        Mobile.destroy();
                        this.sdl.stop();
                        System.exit(0);
                        return 0;
                    case 1073741903:
                        return 54;
                    case 1073741904:
                        return 52;
                    case 1073741905:
                        return 56;
                    case 1073741906:
                        return 50;
                    case 1073741913:
                        return 55;
                    case 1073741914:
                        return 56;
                    case 1073741915:
                        return 57;
                    case 1073741916:
                        return 52;
                    case 1073741917:
                        return 53;
                    case 1073741918:
                        return 54;
                    case 1073741919:
                        return 49;
                    case 1073741920:
                        return 50;
                    case 1073741921:
                        return 51;
                    case 1073741922:
                        return 48;
                    default:
                        return 0;
                }
        }
    }

    private void setPhoneMode(int i) {
        if (i < 0 || i > 4) {
            return;
        }
        this.useFlag = i;
        this.config.settings.put("phone", new String[]{"p", "n", "e", "s", "m"}[i]);
        this.showfps = 0;
        this.config.saveConfig();
    }
}
