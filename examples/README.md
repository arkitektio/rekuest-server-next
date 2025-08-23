# Hook Agent Examples

This directory contains examples of how to implement and use hook agents with the Rekuest server.

## Files

- **`example_hook_agent.py`** - A complete example of a hook agent server implementation
- **`setup_hook_agent.py`** - Script to register the example hook agent with Rekuest

## Quick Start

1. **Start the example hook agent server:**
   ```bash
   python example_hook_agent.py
   ```

2. **Register the hook agent (in another terminal):**
   ```bash
   # First, update the AUTH_TOKEN in setup_hook_agent.py with your actual token
   python setup_hook_agent.py
   ```

3. **Assign tasks to your hook agent using GraphQL or the Rekuest UI**

## Example Hook Agent Features

The example hook agent demonstrates:

- ✅ Receiving task assignments via HTTP POST
- ✅ Authentication using Bearer tokens
- ✅ Progress reporting during task execution
- ✅ Completion reporting with results
- ✅ Error handling and reporting
- ✅ Heartbeat functionality
- ✅ Support for different message types (assign, cancel, interrupt, collect)
- ✅ Simulated task execution based on action types

## Customizing the Example

To adapt this example for your use case:

1. **Update configuration:**
   - Change `REKUEST_BASE_URL` to your Rekuest server URL
   - Generate a unique `SECRET_TOKEN`
   - Update `AGENT_NAME` and `INSTANCE_ID`

2. **Implement your business logic:**
   - Modify the `execute_task()` function to perform your actual work
   - Add support for your specific action types
   - Implement proper error handling for your domain

3. **Production considerations:**
   - Use proper authentication and token management
   - Add logging and monitoring
   - Implement proper error handling and retry logic
   - Use a production WSGI server instead of Flask's development server
   - Add health checks and metrics endpoints

## Dependencies

The example requires:
- Flask (for the web server)
- requests (for HTTP client)

Install them with:
```bash
pip install flask requests
```

## Security Notes

- Always use HTTPS in production
- Keep your secret tokens secure and rotate them regularly
- Validate and sanitize all input data
- Implement proper rate limiting
- Use proper authentication for your GraphQL API access