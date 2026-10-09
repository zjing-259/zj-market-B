package cn.zj.zjmarket.domain.product.model.valobj;

public record ProductSyncProgress(String goodsId,String targetVersion,String targetEventId,String confirmedVersion,String state,String lastError,String checkedAt) {
    public boolean ready(long version){return state.equals("CONFIRMED") && Long.toString(version).equals(targetVersion) && targetVersion.equals(confirmedVersion);}
}
