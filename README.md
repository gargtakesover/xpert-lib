# Xpert - Twitter/X Data Without the Twitter Tax

**Twitter Data for Less Than a Netflix Subscription**

Xpert provides simple, reliable access to Twitter/X data at a fraction of the official API cost.

## Why Xpert?

- **70% cheaper** than Twitter's official API ($29 vs $100+)
- **More reliable** than SNScrape (no more broken scrapers)
- **Simpler** than complex API integrations
- **Free tier** available for testing

## Quick Start

```bash
# Install
pip install xpert

# Get user profile
xpert user elonmusk

# Get timeline
xpert timeline elonmusk --limit 10

# Search tweets
xpert search "python programming"
```

## Installation

```bash
pip install xpert
```

Or install from source:

```bash
git clone https://github.com/xpert/xpert.git
cd xpert
pip install -e .
```

## Configuration

For higher rate limits, configure your API key:

```bash
xpert configure
# Enter your API key from https://xpert.io/dashboard
```

## Library Usage

```python
from xpert import Xpert, get_timeline

# Simple function call
tweets = get_timeline("elonmusk", limit=10)

# Or use the client
client = Xpert(api_key="your_api_key")
user = client.get_user("elonmusk")
tweets = client.get_timeline("elonmusk")

for tweet in tweets:
    print(f"{tweet.text[:50]}... ({tweet.likes} likes)")
```

## Pricing

| Tier | Price | Requests/month | Rate Limit |
|------|-------|----------------|------------|
| Free | $0 | 1,000 | 10/min |
| Starter | $29 | 50,000 | 60/min |
| Pro | $79 | 250,000 | 200/min |
| Business | $199 | 1,000,000 | 500/min |

## API Reference

### `Xpert` Client

```python
client = Xpert(api_key=None)  # Uses public instances (rate limited)
# or
client = Xpert(api_key="xpt_...")  # Uses Xpert API (higher limits)
```

### Methods

- `get_user(username)` - Get user profile
- `get_timeline(username, limit=20)` - Get recent tweets
- `search(query, limit=20)` - Search tweets

### Responses

All methods return typed objects:

```python
@dataclass
class Tweet:
    id: str
    text: str
    author: str
    created_at: str
    url: str
    likes: int = 0
    retweets: int = 0
    replies: int = 0

@dataclass
class User:
    username: str
    display_name: str
    bio: str
    followers: int
    following: int
    tweets: int
    url: str
```

## Open Source

The Xpert library is open source (MIT license). The SaaS service provides:

- Higher rate limits
- Webhook support for real-time alerts
- Historical data access
- Priority support

## Links

- Documentation: https://docs.xpert.io
- Dashboard: https://xpert.io/dashboard
- GitHub: https://github.com/xpert/xpert

---

*"Twitter Data Without the Twitter Tax"*
