// Java fixture. Set sonar.java.binaries (see sonar-project.properties).
public class Main {
    private static final String PASSWORD = "hunter2"; // hard-coded credential

    public static void main(String[] args) {
        int unused = 5; // unused local variable
        String text = null;
        System.out.println(text.length()); // possible NullPointerException
        try {
            Integer.parseInt("x");
        } catch (Exception e) {
            // empty catch block
        }
        if (args.length == 0) {
            return;
        } else {
            return;
        }
    }
}
