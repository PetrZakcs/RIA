import stripe
import os
from dotenv import load_dotenv

def setup_products():
    # Load keys
    # Load keys
    api_key = os.getenv("STRIPE_SECRET_KEY")

    
    if not api_key:
        print("❌ Error: STRIPE_SECRET_KEY not found in env.")
        return

    stripe.api_key = api_key
    print(f"🔹 Authenticated with Stripe (Key: ...{api_key[-4:]})")

    products = [
        {
            "name": "RIA Basic",
            "description": "Max 1 Region, 30m Scan Frequency",
            "price_czk": 2490,
            "id_keyword": "basic" 
        },
        {
            "name": "RIA Business",
            "description": "Whole CZ, Real-time Scan, Advanced AI",
            "price_czk": 6900,
            "id_keyword": "business"
        },
        {
            "name": "RIA Enterprise",
            "description": "Custom Integration, Unlimited",
            "price_czk": 15900,
            "id_keyword": "enterprise"
        }
    ]

    generated_ids = {}

    for p in products:
        try:
            # 1. Create Product
            print(f"Creating Product: {p['name']}...")
            prod = stripe.Product.create(name=p["name"], description=p["description"])
            
            # 2. Create Price
            price = stripe.Price.create(
                product=prod.id,
                unit_amount=p["price_czk"] * 100, # Cents
                currency="czk",
                recurring={"interval": "month"},
            )
            print(f"  ✅ Created! Product ID: {prod.id}, Price ID: {price.id}")
            generated_ids[p["id_keyword"]] = price.id
            
        except Exception as e:
            print(f"  Warning: {e}")
            
    print("\n--- SAVE THESE IDS ---")
    for k, v in generated_ids.items():
        print(f"{k.upper()}_PRICE_ID={v}")

if __name__ == "__main__":
    # Simulate loading or just set raw for this run if .env is tricky
    # We will rely on .env being set by the previous step
    load_dotenv()
    setup_products()
