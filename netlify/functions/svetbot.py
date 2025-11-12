import sys
import os

# Добавляем путь к нашему коду
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from netlify.functions.bot import handler

def main(event, context):
    return handler(event, context)

# Netlify entry point
def lambda_handler(event, context):
    return handler(event, context)