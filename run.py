"""Plaxtra single-command launcher."""
import os
import uvicorn

if __name__ == '__main__':
    uvicorn.run('plaxtra.app:app',host=os.getenv('PLAXTRA_HOST','0.0.0.0'),port=int(os.getenv('PLAXTRA_PORT','8000')),reload=False)
