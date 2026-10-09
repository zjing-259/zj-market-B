package cn.zj.zjmarket.types.exception;

public final class SyncTransportFailure extends RuntimeException {
        private final String code;private final boolean permanent;
        public SyncTransportFailure(String code,boolean permanent){super(code);this.code=code;this.permanent=permanent;}
        public String code(){return code;}public boolean permanent(){return permanent;}
    }
