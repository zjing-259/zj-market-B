package cn.zj.zjmarket.domain.inventory.model.valobj;
import java.util.List;
public record InventoryPage<T>(List<T> items,int page,int size,long total) {}
