# Assota Medical Chatbot - LangGraph React Agent with ClickHouse Integration

A sophisticated medical chatbot for Assota hospital that combines LangGraph's React (Reasoning and Acting) pattern with ClickHouse MCP (Model Context Protocol) integration to provide intelligent, context-aware responses about patient appointments and medical data.

## 🌟 Features

### Core Capabilities
- **LangGraph React Agent**: Advanced reasoning and acting pattern for complex medical queries
- **ClickHouse MCP Integration**: Real-time connection to ClickHouse Cloud database
- **Hebrew Language Support**: Native Hebrew responses for Israeli medical environment
- **Router Logic**: Intelligent routing between general conversation and medical data queries
- **User Privacy**: Secure user_id filtering ensures data privacy compliance
- **LangGraph Studio**: Visual debugging and development interface

### Supported Query Types
- **Appointment Management**: View upcoming appointments, past visits, appointment history
- **Medical Data**: Access to various medical records and test results
- **General Conversation**: Small talk and general hospital information
- **Multi-location Support**: Handles appointments across all Assota locations

## 🏗️ Architecture

### LangGraph React Agent Flow
```
User Query → Router → [Medical Data Query | General Conversation]
     ↓              ↓                    ↓
   Hebrew      ClickHouse MCP      Direct Response
  Response    ← SQL Generation              ↓
     ↑              ↓              Hebrew Response
Final Answer ← Data Processing
```

### Key Components
- **`working_react_agent.py`**: Main LangGraph React agent with ClickHouse integration
- **`clickhouse_mcp_proper.py`**: Async MCP client for ClickHouse connectivity  
- **`langgraph.json`**: LangGraph Studio configuration
- **`app_langgraph.py`**: Flask web interface for the agent
- **`clickhouse_mcp_agent.py`**: Alternative MCP implementation

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key
- ClickHouse Cloud access
- uv package manager

### 1. Environment Setup

Create `.env` file:
```env
# OpenAI Configuration
OPENAI_API_KEY="your-openai-api-key"

# ClickHouse Cloud Configuration  
CLICKHOUSE_HOST=your-clickhouse-host.clickhouse.cloud
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your-password
CLICKHOUSE_SECURE=true
CLICKHOUSE_VERIFY=true
CLICKHOUSE_CONNECT_TIMEOUT=30
CLICKHOUSE_SEND_RECEIVE_TIMEOUT=30

# LangSmith (Optional)
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY="your-langsmith-key"
LANGCHAIN_PROJECT=assota-txt2sql-poc
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install LangGraph CLI with memory support
pip install "langgraph-cli[inmem]>=0.3.6"

# Install ClickHouse MCP
uv add mcp-clickhouse
```

### 3. Run LangGraph Studio

```bash
# Start the development server
langgraph dev

# Open LangGraph Studio
# Navigate to http://localhost:8123
```

### 4. Test the Agent

In LangGraph Studio, test with:
```json
{
  "user_input": "מה התורים שלי?",
  "user_id": "your-user-id",
  "messages": [],
  "thought": "",
  "action": "",
  "action_input": "",
  "observation": "",
  "final_answer": "",
  "iteration": 0
}
```

## 🔧 Development

### Project Structure
```
├── working_react_agent.py      # Main LangGraph React agent
├── clickhouse_mcp_proper.py    # Async MCP ClickHouse client
├── langgraph.json              # LangGraph Studio config
├── app_langgraph.py            # Flask web interface
├── clickhouse_mcp_agent.py     # Alternative MCP implementation
├── langgraph_config.py         # LangGraph configuration
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Project configuration
└── .env                        # Environment variables
```

### Key Files

#### `working_react_agent.py`
The main React agent that:
- Routes queries between conversation and medical data
- Generates SQL queries with proper user_id filtering
- Manages async ClickHouse MCP sessions
- Provides Hebrew responses

#### `clickhouse_mcp_proper.py`
Async MCP client that:
- Handles ClickHouse Cloud connections
- Executes SQL queries via MCP protocol
- Manages session lifecycle properly

### Running Tests

```bash
# Test the React agent directly
python working_react_agent.py

# Test ClickHouse connectivity
python clickhouse_mcp_proper.py
```

## 🌐 Web Interface

### Flask Application

```bash
# Run the web interface
python app_langgraph.py

# Access at http://localhost:5000
```

### Docker Deployment

```bash
# Build image
docker build -t assota-langgraph-chatbot .

# Run container
docker run -p 5000:5000 --env-file .env assota-langgraph-chatbot
```

## 🔒 Security & Privacy

### Data Protection
- **User ID Filtering**: All SQL queries include mandatory `WHERE user_id = 'user_id'` clauses
- **Query Validation**: Prevents SQL injection and unauthorized data access
- **Environment Variables**: Sensitive credentials stored securely in `.env`

### ClickHouse Security
- TLS encryption for all connections
- Certificate verification enabled
- Timeout configurations for connection management

## 📊 Database Schema

### ClickHouse Table: `appointments_cleaned_for_bigquery`

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | String | Patient identifier (mandatory filter) |
| `appointment_date_time_c` | DateTime64 | Appointment date and time |
| `appoitment_type` | String | Type of appointment (note: missing 'n') |
| `appointment_status` | String | Current status |
| `site_name` | String | Hospital location |
| `site_address` | String | Full address |
| `record_type` | String | Record classification |

## 🎯 Usage Examples

### Medical Data Queries (Hebrew)
- `"מה התורים שלי?"` - "What are my appointments?"
- `"תורים קרובים"` - "Upcoming appointments"  
- `"היסטוריית רפואית"` - "Medical history"

### General Conversation (Hebrew)
- `"שלום"` - "Hello"
- `"איך אני יכול לעזור?"` - "How can I help?"
- `"מידע על בית החולים"` - "Hospital information"

## 🔧 Configuration

### LangGraph Studio Settings

The `langgraph.json` file configures:
```json
{
  "python_path": "working_react_agent.py",
  "graph_id": "react_agent",
  "config": {
    "env_file": ".env"
  }
}
```

### OpenAI Model Configuration
- Model: `gpt-4o-mini`
- Temperature: `0.1` (for consistent medical responses)
- Hebrew language optimization

## 🚀 Deployment

### Production Considerations
1. **Environment Variables**: Ensure all credentials are properly configured
2. **ClickHouse Performance**: Monitor query performance and connection pooling
3. **LangSmith Monitoring**: Enable tracing for production debugging
4. **Error Handling**: Comprehensive error handling for MCP connections

### Scaling
- **Async Architecture**: Built for concurrent user sessions
- **Connection Management**: Proper MCP session lifecycle management
- **Caching**: Consider implementing query result caching for common requests

## 🔍 Monitoring & Debugging

### LangGraph Studio
- Visual workflow debugging
- Step-by-step execution tracing
- Real-time state inspection

### LangSmith Integration
- Request/response logging
- Performance analytics
- Error tracking and analysis

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test with LangGraph Studio
4. Submit a pull request

## 📄 License

This project is part of Assota hospital's digital transformation initiative.

---

**Built with ❤️ for Assota Medical Center using LangGraph + ClickHouse MCP**