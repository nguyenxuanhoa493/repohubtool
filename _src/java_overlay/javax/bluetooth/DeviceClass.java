package javax.bluetooth;

public class DeviceClass {
    private int record;

    public DeviceClass(int record) {
        this.record = record;
    }

    public int getServiceClasses() {
        return this.record & 0xFFE000;
    }

    public int getMajorDeviceClass() {
        return this.record & 0x1F00;
    }

    public int getMinorDeviceClass() {
        return this.record & 0xFC;
    }
}
