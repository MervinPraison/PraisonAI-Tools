"""Shopify Tool for PraisonAI Agents.

Manage Shopify store products and orders.

Usage:
    from praisonai_tools import ShopifyTool
    
    shopify = ShopifyTool()
    products = shopify.list_products()

Environment Variables:
    SHOPIFY_SHOP_URL: Shopify shop URL (e.g., mystore.myshopify.com)
    SHOPIFY_ACCESS_TOKEN: Shopify Admin API access token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ShopifyTool(BaseTool):
    """Tool for Shopify store operations."""
    
    name = "shopify"
    description = "Manage Shopify products, orders, and customers."
    
    def __init__(
        self,
        shop_url: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        self.shop_url = shop_url or os.getenv("SHOPIFY_SHOP_URL")
        self.access_token = access_token or os.getenv("SHOPIFY_ACCESS_TOKEN")
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.shop_url or not self.access_token:
            return {"error": "SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN required"}
        
        url = f"https://{self.shop_url}/admin/api/2024-01/{endpoint}.json"
        headers = {"X-Shopify-Access-Token": self.access_token, "Content-Type": "application/json"}
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                resp = requests.put(url, headers=headers, json=data, timeout=10)
            else:
                return {"error": f"Unknown method: {method}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "list_products",
        product_id: Optional[int] = None,
        order_id: Optional[int] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_products":
            return self.list_products(**kwargs)
        elif action == "get_product":
            return self.get_product(product_id=product_id)
        elif action == "list_orders":
            return self.list_orders(**kwargs)
        elif action == "get_order":
            return self.get_order(order_id=order_id)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_products(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List products."""
        result = self._request("GET", f"products?limit={limit}")
        if "error" in result:
            return [result]
        
        products = []
        for p in result.get("products", []):
            products.append({
                "id": p["id"],
                "title": p["title"],
                "vendor": p.get("vendor"),
                "status": p.get("status"),
                "variants_count": len(p.get("variants", [])),
            })
        return products
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Get product details."""
        if not product_id:
            return {"error": "product_id is required"}
        
        result = self._request("GET", f"products/{product_id}")
        if "error" in result:
            return result
        
        p = result.get("product", {})
        return {
            "id": p.get("id"),
            "title": p.get("title"),
            "description": p.get("body_html", "")[:500],
            "vendor": p.get("vendor"),
            "product_type": p.get("product_type"),
            "status": p.get("status"),
            "variants": [
                {"id": v["id"], "title": v["title"], "price": v["price"], "inventory": v.get("inventory_quantity")}
                for v in p.get("variants", [])
            ],
        }
    
    def list_orders(self, limit: int = 50, status: str = "any") -> List[Dict[str, Any]]:
        """List orders."""
        result = self._request("GET", f"orders?limit={limit}&status={status}")
        if "error" in result:
            return [result]
        
        orders = []
        for o in result.get("orders", []):
            orders.append({
                "id": o["id"],
                "order_number": o.get("order_number"),
                "total_price": o.get("total_price"),
                "financial_status": o.get("financial_status"),
                "fulfillment_status": o.get("fulfillment_status"),
                "created_at": o.get("created_at"),
            })
        return orders
    
    def get_order(self, order_id: int) -> Dict[str, Any]:
        """Get order details."""
        if not order_id:
            return {"error": "order_id is required"}
        
        result = self._request("GET", f"orders/{order_id}")
        if "error" in result:
            return result
        
        o = result.get("order", {})
        return {
            "id": o.get("id"),
            "order_number": o.get("order_number"),
            "email": o.get("email"),
            "total_price": o.get("total_price"),
            "subtotal_price": o.get("subtotal_price"),
            "financial_status": o.get("financial_status"),
            "fulfillment_status": o.get("fulfillment_status"),
            "line_items": [
                {"title": li["title"], "quantity": li["quantity"], "price": li["price"]}
                for li in o.get("line_items", [])
            ],
        }


def list_shopify_products(limit: int = 50) -> List[Dict[str, Any]]:
    """List Shopify products."""
    return ShopifyTool().list_products(limit=limit)
