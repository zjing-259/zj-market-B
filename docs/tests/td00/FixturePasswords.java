import org.springframework.security.crypto.argon2.Argon2PasswordEncoder;
import java.io.*;
/** Reads temporary fixture passwords on stdin; callers store outputs privately. */
public final class FixturePasswords {
    public static void main(String[] args) throws Exception {
        Argon2PasswordEncoder encoder = new Argon2PasswordEncoder(16,32,1,19456,2);
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, "UTF-8"));
        String line;
        while ((line=in.readLine())!=null) System.out.println("{argon2id}"+encoder.encode(line));
    }
}
