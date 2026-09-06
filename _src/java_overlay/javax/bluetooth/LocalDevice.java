package javax.bluetooth;

public class LocalDevice {
    private static LocalDevice instance;

    private LocalDevice() {
    }

    public static synchronized LocalDevice getLocalDevice() throws BluetoothStateException {
        if (instance == null) {
            instance = new LocalDevice();
        }
        return instance;
    }

    public DiscoveryAgent getDiscoveryAgent() {
        return new DiscoveryAgent();
    }

    public String getFriendlyName() {
        return "FreeJ2ME";
    }

    public DeviceClass getDeviceClass() {
        return new DeviceClass(0);
    }

    public boolean setDiscoverable(int mode) throws BluetoothStateException {
        return false;
    }

    public static boolean isPowerOn() {
        return true;
    }

    public int getDiscoverable() {
        return 0;
    }

    public String getBluetoothAddress() {
        return "001122334455";
    }

    public static String getProperty(String property) {
        if ("bluetooth.api.version".equals(property)) return "1.0";
        if ("bluetooth.master.switch".equals(property)) return "true";
        return null;
    }

    public ServiceRecord getRecord(javax.microedition.io.Connection notifier) {
        return null;
    }

    public void updateRecord(ServiceRecord srvRecord) throws ServiceRegistrationException {
    }
}
