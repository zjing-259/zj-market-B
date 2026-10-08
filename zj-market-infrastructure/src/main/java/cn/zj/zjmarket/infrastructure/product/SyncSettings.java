package cn.zj.zjmarket.infrastructure.product;
import org.springframework.boot.context.properties.ConfigurationProperties;
@ConfigurationProperties("b.sync")
public class SyncSettings {
 private boolean enabled=false,schedulerEnabled=true,acceleratedTest=false;
 private long scanMillis=2000,leaseMillis=30000,queryMillis=30000;
 private int batchSize=20,maxReconsumeTimes=8;
 private String previousAKeys="";
 public boolean isEnabled(){return enabled;}public void setEnabled(boolean v){enabled=v;}
 public boolean isSchedulerEnabled(){return schedulerEnabled;}public void setSchedulerEnabled(boolean v){schedulerEnabled=v;}
 public boolean isAcceleratedTest(){return acceleratedTest;}public void setAcceleratedTest(boolean v){acceleratedTest=v;}
 public long getScanMillis(){return scanMillis;}public void setScanMillis(long v){scanMillis=v;}
 public long getLeaseMillis(){return leaseMillis;}public void setLeaseMillis(long v){leaseMillis=v;}
 public long getQueryMillis(){return queryMillis;}public void setQueryMillis(long v){queryMillis=v;}
 public int getBatchSize(){return batchSize;}public void setBatchSize(int v){batchSize=v;}
 public int getMaxReconsumeTimes(){return maxReconsumeTimes;}public void setMaxReconsumeTimes(int v){maxReconsumeTimes=v;}
 public String getPreviousAKeys(){return previousAKeys;}public void setPreviousAKeys(String v){previousAKeys=v;}
}
