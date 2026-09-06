package javax.bluetooth;

public class DiscoveryAgent {
    public static final int NOT_DISCOVERABLE = 0;
    public static final int GIAC = 10390323;
    public static final int LIAC = 10390272;
    public static final int CACHED = 0;
    public static final int PREKNOWN = 1;

    public RemoteDevice[] retrieveDevices(int option) {
        return null;
    }

    public boolean startInquiry(int accessCode, DiscoveryListener listener) throws BluetoothStateException {
        return false;
    }

    public boolean cancelInquiry(DiscoveryListener listener) {
        return false;
    }

    public int searchServices(int[] attrSet, UUID[] uuidSet, RemoteDevice btDev, DiscoveryListener listener) throws BluetoothStateException {
        return 0;
    }

    public boolean cancelServiceSearch(int transID) {
        return false;
    }

    public String selectService(UUID uuid, int security, boolean master) throws BluetoothStateException {
        return null;
    }
}
