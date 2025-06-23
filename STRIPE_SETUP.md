# Stripe Setup Guide for RabbitReels

This guide will walk you through setting up Stripe for the RabbitReels billing system.

## 1. Create a Stripe Account

1. Go to [https://stripe.com](https://stripe.com)
2. Click "Start now" or "Sign up"
3. Create your account with email and password
4. Complete the account verification process

## 2. Get Your API Keys

### Test Keys (for development):

1. Log into your Stripe Dashboard
2. Make sure you're in **Test mode** (toggle in the left sidebar should show "Test data")
3. Go to **Developers** → **API keys**
4. You'll see:
   - **Publishable key** (starts with `pk_test_...`)
   - **Secret key** (starts with `sk_test_...`, click "Reveal live key token")

### Production Keys (for live payments):

1. Switch to **Live mode** in the Stripe Dashboard
2. Go to **Developers** → **API keys**
3. You'll see:
   - **Publishable key** (starts with `pk_live_...`)
   - **Secret key** (starts with `sk_live_...`)

⚠️ **Never commit production keys to version control!**

## 3. Set Up Webhooks

Webhooks allow Stripe to notify your application when payments are completed.

### Create a Webhook Endpoint:

1. In Stripe Dashboard, go to **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Set the endpoint URL:
   - **Development**: `http://localhost:8080/billing/webhook`
   - **Production**: `https://yourdomain.com/billing/webhook`
4. Select events to send:
   - `checkout.session.completed`
   - `checkout.session.async_payment_succeeded`
   - `checkout.session.async_payment_failed`
5. Click **Add endpoint**
6. Copy the **Signing secret** (starts with `whsec_...`)

## 4. Configure Environment Variables

### For Development (.env file):

Create or update your `.env` file in the project root:

```bash
# Stripe Test Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Other existing configuration...
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
# ... etc
```

### For Production:

Set environment variables on your production server:

```bash
export STRIPE_SECRET_KEY=sk_live_your_production_secret_key
export STRIPE_PUBLISHABLE_KEY=pk_live_your_production_publishable_key
export STRIPE_WEBHOOK_SECRET=whsec_your_production_webhook_secret
```

## 5. Test Your Setup

### Test with Stripe Test Cards:

Use these test card numbers in your application:

- **Successful payment**: `4242424242424242`
- **Declined payment**: `4000000000000002`
- **Requires authentication**: `4000002500003155`

**Test card details:**
- Any future expiry date (e.g., 12/34)
- Any 3-digit CVC
- Any billing postal code

### Run the Billing Test:

```bash
cd api
python test_billing_e2e.py
```

### Test a Real Purchase Flow:

1. Start your application:
   ```bash
   # Terminal 1: Start services
   docker-compose up -d
   
   # Terminal 2: Start API
   cd api
   python main.py
   
   # Terminal 3: Start frontend
   cd web
   npm run dev
   ```

2. Open http://localhost:3001
3. Sign in with Google
4. Go to the billing page
5. Try purchasing credits with test card `4242424242424242`

## 6. Verify Payments in Stripe Dashboard

1. Go to **Payments** in your Stripe Dashboard
2. You should see test payments appear when you make purchases
3. Check the **Events** section to see webhook deliveries

## 7. Production Checklist

Before going live:

- [ ] Replace test keys with production keys
- [ ] Update webhook endpoint to production URL
- [ ] Test with small amounts first
- [ ] Set up proper error monitoring
- [ ] Configure proper logging
- [ ] Set up Stripe's radar for fraud protection
- [ ] Review and set up proper refund policies

## 8. Troubleshooting

### Common Issues:

**"Webhook not configured" error:**
- Make sure `STRIPE_WEBHOOK_SECRET` is set in your environment

**"Invalid API key" error:**
- Check that your `STRIPE_SECRET_KEY` is correct and not expired
- Make sure you're using the right key for test/live mode

**Payments not completing:**
- Check webhook endpoint is accessible from the internet
- Verify webhook events are being delivered in Stripe Dashboard
- Check your application logs for webhook processing errors

**CORS errors on frontend:**
- Make sure your frontend is using the correct Stripe publishable key
- Check that your domain is properly configured

### Useful Stripe CLI Commands:

Install Stripe CLI for local webhook testing:

```bash
# Install Stripe CLI (Windows)
# Download from: https://github.com/stripe/stripe-cli/releases

# Login to your account
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8080/billing/webhook

# This will give you a webhook secret starting with whsec_...
# Use this for STRIPE_WEBHOOK_SECRET in development
```

## 9. Security Best Practices

1. **Never expose secret keys** in client-side code
2. **Use environment variables** for all sensitive data
3. **Validate webhook signatures** (already implemented)
4. **Use HTTPS** in production
5. **Monitor for suspicious activity** in Stripe Dashboard
6. **Set up proper access controls** for your Stripe account
7. **Regularly rotate API keys** if compromised

## 10. Next Steps

Once Stripe is configured:

1. **Implement subscription billing** (if needed for recurring charges)
2. **Add payment history** for users
3. **Set up automated invoicing** for business customers
4. **Implement refund functionality**
5. **Add payment analytics** and reporting

---

## Support

- **Stripe Documentation**: https://stripe.com/docs
- **Stripe Support**: Available in your Stripe Dashboard
- **RabbitReels Issues**: Create an issue in your project repository
