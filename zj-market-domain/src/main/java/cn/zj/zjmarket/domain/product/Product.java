package cn.zj.zjmarket.domain.product;
import java.math.BigDecimal;
import java.net.URI;
import java.util.regex.Pattern;
/** B's authoritative single-SKU fact. All effective edits share one version. */
public record Product(String goodsId, Fields fields, long version, long createdAt, long updatedAt) {
    public enum SaleStatus { ON_SALE, OFF_SALE }
    public record Fields(String goodsName,String description,String imageUrl,BigDecimal originalPrice,String currency,SaleStatus saleStatus) {
        private static final Pattern HTML=Pattern.compile("(?is)<\\s*(?:/?[a-z][^>]*|![^>]*|\\?[^>]*)>");
        public Fields(String goodsName,String description,String imageUrl,String price,String currency,SaleStatus status){this(goodsName,description,imageUrl,money(price),currency,status);}
        private static BigDecimal money(String value){
            if(value==null || !value.matches("(?:0\\.(?:0[1-9]|[1-9][0-9])|[1-9][0-9]{0,5}\\.[0-9]{2})"))throw new IllegalArgumentException("Invalid money");
            return new BigDecimal(value);
        }
        public Fields {
            if(goodsName==null || description==null || currency==null || saleStatus==null)throw new IllegalArgumentException("Invalid product fields");
            goodsName=goodsName.strip().trim();
            if(goodsName.isEmpty() || goodsName.length()>128 || description.codePointCount(0,description.length())>2000
                || HTML.matcher(description).find() || description.indexOf('\0')>=0 || goodsName.indexOf('\0')>=0)throw new IllegalArgumentException("Invalid text");
            if(originalPrice==null || originalPrice.scale()!=2 || originalPrice.compareTo(new BigDecimal("0.01"))<0 || originalPrice.compareTo(new BigDecimal("999999.99"))>0 || !currency.equals("CNY"))throw new IllegalArgumentException("Invalid money");
            if(imageUrl!=null){
                if(imageUrl.length()>2048 || !imageUrl.matches("https://[^\\s]+") || imageUrl.codePoints().anyMatch(c -> Character.isISOControl(c) || Character.isWhitespace(c) || Character.isSpaceChar(c)))throw new IllegalArgumentException("Invalid image URL");
                try{var url=URI.create(imageUrl);if(url.getHost()==null || url.getUserInfo()!=null)throw new IllegalArgumentException("Invalid image host");}
                catch(IllegalArgumentException e){throw new IllegalArgumentException("Invalid image URL");}
            }
        }
    }
    public Product {
        if(goodsId==null || !goodsId.matches("[A-Za-z0-9._-]{1,64}") || version<1 || fields==null)throw new IllegalArgumentException("Invalid product");
    }
    public Product edit(Fields next,long now){if(fields.equals(next))return this;if(version==Long.MAX_VALUE)throw new ArithmeticException("Product version exhausted");return new Product(goodsId,next,version+1,createdAt,now);}
    public static long parseVersion(String value){
        if(value==null || !value.matches("[1-9][0-9]{0,18}"))throw new IllegalArgumentException("Invalid version");
        try{return Long.parseLong(value);}catch(NumberFormatException e){throw new IllegalArgumentException("Invalid version");}
    }
}
