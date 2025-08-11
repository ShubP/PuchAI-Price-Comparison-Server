# Price Comparison MCP Server for Puch AI

This MCP server lets Puch compare product prices across a strict set of sources using a single upstream data source (Google Shopping via the Serper API).

Supported sources:
- Amazon
- Blinkit
- Zepto
- Swiggy Instamart

All results come from Google Shopping data queried through the Serper API. Results from other sites are ignored.

## 🚀 Features

### Tools

1. **price_comparison** — Search prices for a specific product across Amazon, Blinkit, Zepto, and Swiggy Instamart. Returns product title, price, platform, and direct link.
2. **price_search** — Alias of `price_comparison`.

### Data Source and Filtering

- Data source: Google Shopping via Serper API
- Only these sources are returned: Amazon, Blinkit, Zepto, Swiggy Instamart
- If none of the above sources are found, the server responds: “We couldn't find the requested product on online quick commerce sites.”

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.11 or higher
- A Puch AI account
- Your WhatsApp number

### Step 1: Install Dependencies

```bash
# Navigate to the price comparison directory
cd PuchAI-price-comparison

# Install required packages
pip install -r requirements.txt
```

### Step 2: Configure Environment

Create a `.env` file in the `PuchAI-price-comparison` directory:

```env
AUTH_TOKEN=your_secret_token_here
MY_NUMBER=919876543210
SERPER_API_KEY=your_serper_api_key
```

**Important Notes:**
- `AUTH_TOKEN`: Your secret token for authentication (keep it secure!)
- `MY_NUMBER`: Your WhatsApp number in format `{country_code}{number}` (e.g., `919876543210` for +91-9876543210)

### Step 3: Run the Server

```bash
python mcp_price_comparison.py
```

You'll see: `🚀 Starting Price Comparison MCP server on http://0.0.0.0:8086`

### Step 4: Make It Public (Required by Puch)

Since Puch needs to access your server over HTTPS, you need to expose your local server:

#### Option A: Using ngrok (Recommended for Development)

1. **Install ngrok:**
   Download from https://ngrok.com/download

2. **Get your authtoken:**
   - Go to https://dashboard.ngrok.com/get-started/your-authtoken
   - Copy your authtoken
   - Run: `ngrok config add-authtoken YOUR_AUTHTOKEN`

3. **Start the tunnel:**
   ```bash
   ngrok http 8086
   ```

#### Option B: Deploy to Cloud (Recommended for Production)

Deploy to services like:
- **Railway** - Easy deployment with GitHub integration
- **Render** - Free tier available
- **Heroku** - Reliable cloud platform
- **DigitalOcean App Platform** - Scalable solution

## 🔗 Connect with Puch AI

1. **[Open Puch AI](https://wa.me/+919998881729)** in your browser
2. **Start a new conversation**
3. **Use one of the connect commands:**

   - Bearer Token (recommended):
     ```
     /mcp connect https://your-domain.ngrok.app/mcp your_secret_token_here
     ```

     Your MCP server will expose a `validate` tool that accepts the bearer token and returns your phone number in the format `{country_code}{number}`.

   - OAuth (if you implement it separately):
     ```
     /mcp connect https://your-domain.ngrok.app/mcp
     ```

### Debug Mode

To get more detailed error messages:

```
/mcp diagnostics-level debug
```

## 🛒 Examples

Ask Puch any of the following:
```
Compare prices for iPhone 15 128GB
Check price of Amul milk 500ml
Find price for Coca Cola 2L
```

## 💡 Use Cases

### For Consumers
- **Smart Shopping**: Compare prices before making purchases
- **Budget Planning**: Find the best deals within your budget
- **Quick Commerce**: Get groceries delivered in minutes
- **Price Tracking**: Wait for the best time to buy

### For Businesses
- **Market Research**: Monitor competitor pricing
- **Price Optimization**: Understand market trends
- **Inventory Planning**: Track product availability

## 🔧 Technical Details

### Architecture
- **FastMCP** — MCP server framework
- **Async/Await** — Non-blocking I/O operations
- **Pydantic** — Data validation and serialization

### Data Source
- **Serper API** (Google Shopping)

### Security
- **Bearer Token Authentication**: Secure access control
- **HTTPS Required**: All connections must be encrypted
- **Rate Limiting**: Prevents abuse of external APIs

## 🚨 Important Notes

### Free Tier Limitations
- This server uses free data sources and APIs
- Some platforms may have rate limiting
- Web scraping is used where APIs are not available

### Legal Compliance
- Respect robots.txt files
- Implement appropriate delays between requests
- Follow platform terms of service

### Production Considerations
- Implement proper error handling
- Add caching for better performance
- Monitor API rate limits
- Set up logging and monitoring

## 🐛 Troubleshooting

### Common Issues

1. **Connection Failed**
   - Ensure your server is running on port 8086
   - Check that ngrok (or your hosting) is properly configured over HTTPS
   - Verify your AUTH_TOKEN is correct

2. **No Price Results**
   - Ensure `SERPER_API_KEY` is set and valid
   - Try different search keywords
   - If results exist only on non-supported sites, they will be filtered out

3. **Authentication Error**
   - Verify your `MY_NUMBER` format (country code + number)
   - Check that `AUTH_TOKEN` matches what you use in Puch

### Debug Commands

```bash
# Check server status
curl http://localhost:8086/health

# Test authentication
curl -H "Content-Type: application/json" -d '{"id":1,"jsonrpc":"2.0","method":"tools/call","params":{"name":"validate","arguments":{"bearer_token":"YOUR_TOKEN"}}}' http://localhost:8086/mcp | jq
```

## 🤝 Contributing

This is a hackathon project designed to be useful for the Puch AI community. Feel free to:

- Add support for more platforms
- Improve price accuracy
- Add new features
- Report bugs and issues

## 📞 Support

- **Puch AI Discord:** https://discord.gg/VMCnMvYx
- **Puch AI Documentation:** https://puch.ai/mcp
- **Puch WhatsApp:** +91 99988 81729

## 📄 License

This project is open source and available under the MIT License.

---

**Happy Shopping! 🛒✨**

Use the hashtag `#BuildWithPuch` when sharing your MCP server!
