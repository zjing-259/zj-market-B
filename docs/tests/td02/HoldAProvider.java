package cn.bugstack.test.v2;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
/** Test-only bridge: the TD01 provider binds loopback inside its container. */
public final class HoldAProvider {
 public static void main(String[] args)throws Exception{
  V2TeamDiscoveryLiveTest.start();
  ServerSocket server=new ServerSocket(50052,50,InetAddress.getByName("0.0.0.0"));
  Set<Socket> sockets=Collections.synchronizedSet(new HashSet<Socket>());
  Thread accept=new Thread(()->{while(!server.isClosed())try{
   Socket inbound=server.accept();Socket target=new Socket("127.0.0.1",50051);
   sockets.add(inbound);sockets.add(target);
   pipe(inbound,target);pipe(target,inbound);
  }catch(IOException ignored){}},"td02-test-bridge");accept.setDaemon(true);accept.start();
  System.out.println("TD02_PROVIDER_READY");System.out.flush();
  try{while(!Files.exists(Paths.get("/work/stop")))Thread.sleep(250);}finally{server.close();synchronized(sockets){for(Socket socket:sockets)try{socket.close();}catch(IOException ignored){}}V2TeamDiscoveryLiveTest.stop();}
 }
 private static void pipe(Socket from,Socket to){Thread t=new Thread(()->{try{InputStream input=from.getInputStream();OutputStream output=to.getOutputStream();byte[] bytes=new byte[8192];for(int n;(n=input.read(bytes))!=-1;){output.write(bytes,0,n);output.flush();}}catch(IOException ignored){}finally{try{from.close();}catch(IOException ignored){}try{to.close();}catch(IOException ignored){}}},"td02-tls-pipe");t.setDaemon(true);t.start();}
}
