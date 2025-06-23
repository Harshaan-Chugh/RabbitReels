# 💳 RabbitReels Billing Setup Guide

This guide will help you set up Stripe billing for RabbitReels, allowing users to purchase credits to generate AI videos.

## 🚀 Quick Setup

### 1. Create a Stripe Account

1. Sign up at [stripe.com](https://stripe.com)
2. Complete your account setup
3. Switch to **Test Mode** for development

### 2. Get Your API Keys

1. Go to **Developers** → **API keys** in your Stripe dashboard
2. Copy your **Publishable key** (starts with `pk_test_`)
3. Copy your **Secret key** (starts with `sk_test_`)

### 3. Set Up Environment Variables

Add these to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_actual_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_actual_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

Add this to your `web/.env.local`:

```bash
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_actual_publishable_key_here
```

### 4. Install Dependencies

```bash
# Backend
cd api
pip install stripe==8.12.0

# Frontend  
cd web
npm install @stripe/stripe-js
```

### 5. Set Up Webhooks (Important!)

1. In Stripe Dashboard, go to **Developers** → **Webhooks**
2. Click **+ Add endpoint**
3. URL: `http://localhost:8080/billing/webhook` (or your production URL)
4. Select these events:
   - `checkout.session.completed`
   - `checkout.session.async_payment_succeeded`
   - `checkout.session.async_payment_failed`
5. Copy the **Signing secret** and add it to `STRIPE_WEBHOOK_SECRET`

### 6. Test the Integration

1. Start your services:
   ```bash
   # Terminal 1 - Backend
   cd api
   python main.py
   
   # Terminal 2 - Frontend
   cd web
   npm run dev
   ```

2. Visit `http://localhost:3001/billing`
3. Try purchasing credits with test card: `4242 4242 4242 4242`

## 🎯 How It Works

### Credit System
- **1 credit = 1 video generation**
- Credits are stored in Redis (`credits:user_id`)
- Credits never expire
- Bulk discounts available (10, 50, 100 credit packs)

### Pricing Structure
Default prices (configurable in `api/config.py`):
- 1 credit: $0.50
- 10 credits: $4.50 (10% discount)
- 50 credits: $20.00 (20% discount)  
- 100 credits: $35.00 (30% discount)

### User Flow
1. User tries to generate video
2. System checks credit balance
3. If no credits → redirect to billing page
4. User purchases credits via Stripe Checkout
5. Webhook grants credits to user account
6. User can generate videos

## 🔧 Configuration

### Customizing Credit Prices

Edit `api/config.py`:

```python
CREDIT_PRICES = {
    1: 50,     # $0.50 for 1 credit
    10: 450,   # $4.50 for 10 credits  
    50: 2000,  # $20.00 for 50 credits
    100: 3500  # $35.00 for 100 credits
}
```

### Adding New Credit Packages

1. Add to `CREDIT_PRICES` in `config.py`
2. The billing page will automatically show the new package
3. Discounts are calculated automatically

## 🛡️ Security & Production

### For Production:

1. **Use Live Keys**: Replace test keys with live keys from Stripe
2. **Webhook Security**: Ensure webhook URL is HTTPS
3. **Environment Variables**: Never commit keys to version control
4. **Rate Limiting**: Consider adding rate limiting to prevent abuse
5. **Monitoring**: Set up Stripe dashboard monitoring

### Test Cards (Development):

- **Success**: `4242 4242 4242 4242`
- **Declined**: `4000 0000 0000 0002`
- **Insufficient funds**: `4000 0000 0000 9995`

## 🔍 Troubleshooting

### Common Issues:

1. **Webhook not working**:
   - Check webhook URL is correct
   - Verify webhook secret matches
   - Use `stripe listen --forward-to localhost:8080/billing/webhook` for local testing

2. **Credits not granted**:
   - Check webhook logs in Stripe dashboard
   - Verify Redis connection
   - Check API logs for errors

3. **Payment not processing**:
   - Verify Stripe keys are correct
   - Check browser console for errors
   - Ensure publishable key is set in frontend

### Debug Commands:

```bash
# Check Redis credits
redis-cli get "credits:user_id_here"

# Test webhook locally
stripe listen --forward-to localhost:8080/billing/webhook

# View Stripe logs
# Go to Stripe Dashboard → Developers → Logs
```

## 📈 Scaling Considerations

### For High Volume:

1. **Database**: Move from Redis to PostgreSQL for persistent storage
2. **Caching**: Keep Redis for fast credit checks
3. **Webhooks**: Implement idempotency keys
4. **Monitoring**: Add credit usage analytics
5. **Support**: Implement customer support tools

### Stripe Billing Credits (Advanced):

For larger scale, consider Stripe's native billing credits system:
- Automatic invoicing
- Credit balances managed by Stripe
- Usage-based billing
- See Stripe Billing Credits documentation

## 🎉 That's It!

Your RabbitReels instance now supports credit-based billing! Users can purchase credits and generate AI videos seamlessly.

For support, check the [main README](README.md) or open an issue on GitHub.
