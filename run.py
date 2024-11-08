import asyncio
import uvicorn
import logging
from src.main import app, db, smshub

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def startup():
    """Initialize database and connections"""
    try:
        # Initialize database
        await db.initialize()
        logger.info("Database initialized successfully")
        
        # Test SMSHUB connection
        await smshub.test_connection()
        logger.info("SMSHUB connection verified")
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

async def main():
    # Initialize services
    await startup()
    
    # Configure and run server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise 