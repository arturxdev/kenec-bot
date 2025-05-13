"""
Attendance Software with Telegram and Location Validation

This software allows users to check their attendance using a Telegram bot.
It validates their location against a predefined permission range on a map.

Key Features:
- Telegram Bot Integration: Uses a Telegram bot for user interaction.
- Location Validation: Checks if the user's location is within an allowed range.
- Attendance Logging: Records attendance with timestamps and location data.
- Map-Based Configuration: Uses a map (represented abstractly here) to define allowed areas.
- User Authentication:  Basic user authentication (can be expanded).
- Enhanced Location Handling: Attempts to get *live* location and provides feedback.

Technical Architecture:
1. Telegram Bot:
    - Handles user interactions (start, check-in).
    - Receives user location data.
    - Sends messages and prompts to the user.
2. Location Validation Module:
    - Validates user location against the allowed area.
    - Uses a map representation (can be a set of coordinates, a shapefile, etc.).
3. Data Storage:
    - Stores user data, attendance logs, and potentially map data.
    - (Using in-memory storage for this example, should be replaced with a database)
4. Security:
    - Uses a Telegram bot token for authentication.
    - (Consider secure storage of the token and user data in a production environment)

How it Works:
1. User starts the bot and sends a check-in command.
2. The bot requests the user's location.
3. The user sends their location.
4. The bot validates the location against the allowed area.
5. If the location is valid, attendance is recorded.
6. The bot sends a confirmation message to the user.

Important Considerations:
- Map Representation:  The `is_location_valid` function needs a concrete implementation
  to represent the map and the allowed area.  This could involve:
    -   A list of coordinates defining a polygon.
    -   Using a spatial database (e.g., PostGIS) and performing a spatial query.
    -   Using a library like Shapely to define geometric shapes.
-   Database:  For production, replace the in-memory storage with a proper database
    (e.g., PostgreSQL, MySQL, MongoDB).
-   Error Handling:  Add more robust error handling (e.g., handling invalid location data,
    Telegram API errors).
-   Security:  Implement proper authentication and authorization.  Store sensitive
    data securely (e.g., using environment variables, secure configuration files).
-   Scalability:  Consider how the system will scale with a large number of users.
-   User Interface:  The Telegram bot interface can be enhanced with buttons,
    inline keyboards, and other features.
-   Testing:  Write unit tests and integration tests to ensure the system's reliability.
-   Deployment:  Consider how the bot will be deployed (e.g., on a cloud platform
    like Heroku, AWS, or Google Cloud).
-   Location Spoofing:  This code attempts to mitigate spoofing but cannot completely prevent it.
    Additional measures (e.g., requiring a photo, manual verification) may be needed for high-security scenarios.
"""

import logging
import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackContext,
    ConversationHandler,
    filters,
)
from typing import Dict, Tuple, List
from dotenv import load_dotenv

load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# States for the conversation handler
CHECK_IN = 1
GET_LOCATION = 2

# Maximum number of allowed attempts
MAX_ATTEMPTS = 3

# In-memory storage for user data and attendance records (replace with a database)
user_data: Dict[int, Dict] = {}  # {user_id: {username: str, ...}}
attendance_records: List[Dict] = []  # List of attendance records
attempt_counts: Dict[int, int] = {}  # Track attempts per user

# Telegram Bot Token (replace with your actual token)
#  Use a secure method to store your token (e.g., environment variable)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# Dummy function to simulate location validation
def is_location_valid(latitude: float, longitude: float) -> bool:
    """
    Validates if the given location is within the allowed attendance area.

    This is a placeholder function.  You need to implement the actual logic
    based on how you represent your map and allowed area.

    For example, you might check if the latitude and longitude fall within
    a defined bounding box, or if they are within a certain radius of a
    specified point.  You could also use a more complex geometric
    calculation if your allowed area is a polygon or other shape.

    Args:
        latitude (float): The latitude of the user's location.
        longitude (float): The longitude of the user's location.

    Returns:
        bool: True if the location is valid, False otherwise.
    """
    # Calculate if location is within 5km radius of the center point
    # Using the Haversine formula to calculate distance between two points
    import math
    
    # Center point coordinates
    center_latitude = 19.523731621451685
    center_longitude = -99.2536655776822
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(latitude)
    lon1_rad = math.radians(longitude)
    lat2_rad = math.radians(center_latitude)
    lon2_rad = math.radians(center_longitude)
    
    # Earth radius in kilometers
    earth_radius = 6371.0
    
    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = earth_radius * c
    print(distance)
    
    # Check if within 5km radius
    max_distance = 5.0  # 5 kilometers
    
    print(f"Distance from center: {distance:.2f} km")
    return distance <= max_distance


def record_attendance(
    user_id: int, username: str, latitude: float, longitude: float
) -> None:
    """
    Records the user's attendance with timestamp and location.

    Args:
        user_id (int): The user's Telegram ID.
        username (str): The user's Telegram username.
        latitude (float): The latitude of the user's location.
        longitude (float): The longitude of the user's location.
    """
    timestamp = datetime.datetime.now()
    attendance_records.append(
        {
            "user_id": user_id,
            "username": username,
            "timestamp": timestamp,
            "latitude": latitude,
            "longitude": longitude,
        }
    )
    logger.info(f"Attendance recorded for user {user_id} at {timestamp}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the /start command.  Initializes the user and starts the check-in process.
    """
    user = update.message.from_user
    user_id = user.id
    username = user.username
    if user_id not in user_data:
        user_data[user_id] = {"username": username}  # Store username
        logger.info(f"New user: {user_id}, username: {username}")
    else:
        logger.info(f"Returning user: {user_id}, username: {username}")

    await update.message.reply_text(
        "Verifica tu asistencia con el bot de Telegram.\n"
        "Para verificar tu asistencia, por favor envía el comando /checkin."
    )
    return CHECK_IN  # Go to the CHECK_IN state


async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the /checkin command.  Requests the user's location.  Prompts
    the user to send their *actual* location using the Telegram button.
    """
    user_id = update.message.from_user.id
    # Reset attempt count when starting a new check-in
    attempt_counts[user_id] = 0
    
    # Create a custom keyboard to request the user's location
    keyboard = [
        [KeyboardButton(text="Share your location", request_location=True)],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        "Por favor comparte tu ubicación *actual* usando el botón de abajo para verificar tu asistencia.",
        reply_markup=reply_markup,
    )
    return GET_LOCATION  # Go to the GET_LOCATION state


async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the user's location.  Validates the location, records attendance,
    and sends a confirmation message.
    """
    user = update.message.from_user
    user_id = user.id
    username = user_data[user_id]["username"]  # Retrieve username
    
    # Initialize attempt count if not exists
    if user_id not in attempt_counts:
        attempt_counts[user_id] = 0
    
    if update.message.location:
        location = update.message.location
        latitude = location.latitude
        longitude = location.longitude
        logger.info(f"Received location from user {user_id}: {latitude}, {longitude}")

        if is_location_valid(latitude, longitude):
            record_attendance(user_id, username, latitude, longitude)
            # Reset attempt count on success
            attempt_counts[user_id] = 0
            await update.message.reply_text(
                "Tu asistencia ha sido registrada. Gracias!",
                reply_markup=ReplyKeyboardMarkup(
                    [],
                    one_time_keyboard=True,  # remove keyboard
                ),
            )
            return ConversationHandler.END  # End the conversation
        else:
            # Increment attempt count
            attempt_counts[user_id] += 1
            remaining_attempts = MAX_ATTEMPTS - attempt_counts[user_id]
            
            if remaining_attempts > 0:
                # Create a custom keyboard to request the user's location again
                keyboard = [
                    [KeyboardButton(text="Share your location", request_location=True)],
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
                
                await update.message.reply_text(
                    f"❌ Verificación de ubicación fallida!\n\n"
                    f"Tu ubicación actual está fuera del área permitida. Por favor asegúrate de estar "
                    f"en la ubicación correcta y vuelve a intentarlo.\n\n"
                    f"Intentos restantes: {remaining_attempts}\n"
                    f"Haz clic en el botón de abajo para compartir tu ubicación nuevamente:",
                    reply_markup=reply_markup,
                )
                return GET_LOCATION  # Remain in the GET_LOCATION state to ask again.
            else:
                # Maximum attempts reached
                await update.message.reply_text(
                    "❌ Verificación de asistencia fallida!\n\n"
                    "Has excedido el número máximo de intentos (3). "
                    "Por favor intenta nuevamente o contacta al soporte si crees que esto es un error.",
                    reply_markup=ReplyKeyboardMarkup(
                        [],
                        one_time_keyboard=True,  # remove keyboard
                    ),
                )
                # Reset attempt count
                attempt_counts[user_id] = 0
                return ConversationHandler.END  # End the conversation
    else:
        # Increment attempt count for invalid location data
        attempt_counts[user_id] += 1
        remaining_attempts = MAX_ATTEMPTS - attempt_counts[user_id]
        
        if remaining_attempts > 0:
            # Create a custom keyboard to request the user's location
            keyboard = [
                [KeyboardButton(text="Share your location", request_location=True)],
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            
            await update.message.reply_text(
                f"❌ Invalid location data received!\n\n"
                f"Please use the button below to share your location using Telegram's location sharing feature.\n\n"
                f"Attempts remaining: {remaining_attempts}",
                reply_markup=reply_markup,
            )
            return GET_LOCATION  # Remain in the GET_LOCATION state
        else:
            # Maximum attempts reached
            await update.message.reply_text(
                "❌ Check-in failed!\n\n"
                "You have exceeded the maximum number of attempts (3). "
                "Please try again later or contact support if you believe this is an error.",
                reply_markup=ReplyKeyboardMarkup(
                    [],
                    one_time_keyboard=True,  # remove keyboard
                ),
            )
            # Reset attempt count
            attempt_counts[user_id] = 0
            return ConversationHandler.END  # End the conversation


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.id)
    await update.message.reply_text("Bye! Hope to see you around again.")
    return ConversationHandler.END


def main() -> None:
    """
    Main function to start the Telegram bot.
    """
    application = ApplicationBuilder().token(TOKEN).build()

    # Define conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHECK_IN: [CommandHandler("checkin", checkin)],
            GET_LOCATION: [MessageHandler(filters.LOCATION, get_location)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers to the application
    application.add_handler(conv_handler)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
