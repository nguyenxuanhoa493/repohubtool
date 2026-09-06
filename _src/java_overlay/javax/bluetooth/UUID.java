package javax.bluetooth;

public class UUID {
    private String uuidValue;

    public UUID(long value) {
        this.uuidValue = Long.toHexString(value);
    }

    public UUID(String uuidValue, boolean shortUUID) {
        this.uuidValue = uuidValue;
    }

    public String toString() {
        return this.uuidValue;
    }

    public boolean equals(Object value) {
        if (value instanceof UUID) {
            return this.uuidValue != null && this.uuidValue.equalsIgnoreCase(((UUID) value).uuidValue);
        }
        return false;
    }

    public int hashCode() {
        return this.uuidValue != null ? this.uuidValue.hashCode() : 0;
    }
}
