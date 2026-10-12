import java.net.*;
/** Process liveness only: never creates business work or claims dependency readiness. */
public final class HealthProbe {
 public static void main(String[] args) throws Exception {
  HttpURLConnection c=(HttpURLConnection)new URL(args[0]).openConnection();
  c.setConnectTimeout(2000);c.setReadTimeout(2000);
  int code=c.getResponseCode();c.disconnect();
  if(code!=200)throw new IllegalStateException("Liveness HTTP "+code);
 }
}
