
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import stripe
from src.common.config import settings

router = APIRouter()

# Configure Stripe
if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY

class CheckoutRequest(BaseModel):
    price_id: str
    user_email: str

@router.post("/create-checkout-session")
async def create_checkout_session(data: CheckoutRequest):
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': data.price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url='http://127.0.0.1:8000/payment/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://127.0.0.1:8000/register?canceled=true',
            customer_email=data.user_email,
        )
        return {"url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create-portal-session")
async def create_portal_session(data: CheckoutRequest):
    # This endpoint redirects valid customers to the Stripe Customer Portal
    if not settings.STRIPE_SECRET_KEY:
         raise HTTPException(status_code=500, detail="Stripe not configured")
    
    # In a real app, 'data' would just be user context. 
    # Here we need the stripe_customer_id.
    # Since we don't have the user object in this unauthenticated endpoint easily,
    # we will trust the provided email to look up the user OR 
    # better: We should pass customer_id if known.
    # Limitation: Our User model HAS stripe_customer_id but we don't save it on registration unless webhook works.
    # STRATEGY FOR MVP:
    # Since user registers -> then pays -> Stripe creates customer.
    # We haven't built the Webhook to catch connection yet! 
    # So our DB actually DOES NOT know the stripe_customer_id yet.
    # 
    # WORKAROUND: Use Customer Email search to find the customer in Stripe.
    
    try:
        customers = stripe.Customer.list(email=data.user_email, limit=1)
        if not customers.data:
            # If no customer found, they might be free/basic users never paid Stripe.
            # In that case, we can't show portal.
            return {"url": None, "error": "No billing account found."}
            
        customer = customers.data[0]
        
        portal_session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url="http://127.0.0.1:8000/dashboard",
        )
        return {"url": portal_session.url}
    except Exception as e:
         raise HTTPException(status_code=400, detail=str(e))

@router.get("/success")

async def payment_success(session_id: str):
    # Determine the user from session?
    # For MVP, just show a Success Page
    from fastapi.responses import HTMLResponse
    html_content = """
    <html>
        <head>
            <title>Payment Successful</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f0f0; }
                .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
                h1 { color: #2ecc71; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Payment Successful! 🎉</h1>
                <p>Your subscription is now active.</p>
                <a href="/login">Go to Login</a>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content="""
    <html>
        <head>
            <title>Platba přijata</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f0f0; }
                .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
                h1 { color: #2ecc71; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Platba úspěšná! 🎉</h1>
                <p>Vaše předplatné je nyní aktivní.</p>
                <a href="/login">Přejít na přihlášení</a>
            </div>
        </body>
    </html>
    """)

