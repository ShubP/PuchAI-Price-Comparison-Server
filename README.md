# Price Comparison MCP Server for Puch AI

A powerful Model Context Protocol (MCP) server that provides comprehensive price comparison tools for Indian e-commerce platforms. This server helps users find the best deals across multiple platforms including Amazon, Flipkart, Myntra, Swiggy Instamart, Zepto, and BigBasket.

## 🚀 Features

### Core Tools

1. **Price Comparison** - Compare prices across multiple e-commerce platforms
2. **Quick Price Check** - Fast price lookup for grocery items and essentials
3. **Price Tracker** - Monitor price changes and set price drop alerts
4. **Deal Finder** - Discover the best deals, discounts, and offers

### Supported Platforms

- **Amazon India** - Electronics, books, home goods
- **Flipkart** - Electronics, fashion, home appliances
- **Myntra** - Fashion and lifestyle products
- **Swiggy Instamart** - Groceries and essentials (10-minute delivery)
- **Zepto** - Quick commerce groceries (10-minute delivery)
- **BigBasket** - Groceries and household items

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.11 or higher
- A Puch AI account
- Your WhatsApp number

### Step 1: Install Dependencies

```bash
# Navigate to the price comparison directory
cd mcp-price-comparison

# Install required packages
pip install -r requirements.txt
```

### Step 2: Configure Environment

Create a `.env` file in the `mcp-price-comparison` directory:

```env
AUTH_TOKEN=your_secret_token_here
MY_NUMBER=919876543210
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
3. **Use the connect command:**
   ```
   /mcp connect https://your-domain.ngrok.app/mcp your_secret_token_here
   ```

### Debug Mode

To get more detailed error messages:

```
/mcp diagnostics-level debug
```

## 🛒 Available Tools

### 1. Price Comparison

Compare prices across multiple platforms for any product.

**Usage:**
```
Compare prices for iPhone 15
Find the best price for running shoes
What's the cheapest laptop available?
```

**Features:**
- Multi-platform price comparison
- Best price identification
- Price range analysis
- Availability status
- Customer ratings
- Shipping information

### 2. Quick Price Check

Fast price lookup for grocery items and essentials.

**Usage:**
```
Check milk prices
What's the price of bread?
Compare egg prices
```

**Features:**
- Focused on quick commerce platforms
- 10-30 minute delivery options
- Fresh grocery pricing
- Real-time availability

### 3. Price Tracker

Monitor price changes and set price drop alerts.

**Usage:**
```
Track iPhone 15 prices with target ₹50,000
Monitor laptop prices on Amazon
Set price alert for ₹1000 for running shoes
```

**Features:**
- Price history tracking
- Target price alerts
- Platform-specific monitoring
- Price drop notifications

### 4. Deal Finder

Discover the best deals, discounts, and offers.

**Usage:**
```
Find deals on electronics under ₹5000
Show fashion deals
What grocery deals are available?
```

**Features:**
- Category-specific deals
- Budget range filtering
- Seasonal offers
- Platform-specific discounts

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
- **FastMCP**: High-performance MCP server framework
- **Async/Await**: Non-blocking I/O operations
- **BeautifulSoup**: HTML parsing for web scraping
- **Pydantic**: Data validation and serialization

### Data Sources
- **Web Scraping**: Real-time price data from e-commerce sites
- **Simulated APIs**: For platforms without public APIs
- **Price Databases**: Historical price tracking

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
   - Check that ngrok is properly configured
   - Verify your AUTH_TOKEN is correct

2. **No Price Results**
   - Try different search keywords
   - Check if the product is available in your area
   - Some platforms may be temporarily unavailable

3. **Authentication Error**
   - Verify your MY_NUMBER format (country code + number)
   - Check that AUTH_TOKEN matches what you use in Puch

### Debug Commands

```bash
# Check server status
curl http://localhost:8086/health

# Test authentication
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8086/validate
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
