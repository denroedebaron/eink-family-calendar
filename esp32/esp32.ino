#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <GxEPD2_BW.h>
#include <GxEPD2_3C.h>
#include <epd3c/GxEPD2_750c_Z08.h>
#include <time.h>
#include <esp_task_wdt.h>

// Configuration
const char* WIFI_SSID = "<YOUR WIFI>";
const char* WIFI_PASSWORD = "<YOUR WIFI PASSWORD>";
const char* SERVER_URL = "http://<YOUR IP>:8000";
const char* TIMEZONE = "CET-1CEST,M3.5.0,M10.5.0/3";
const int BACKUP_CHECK_HOURS = 3;
const int MANUAL_UPDATE_PIN = 0;

// ESP32-S3 Display pins
const int PIN_CS   = 10;
const int PIN_DC   = 13;
const int PIN_RST  = 14;
const int PIN_BUSY = 4;
const int PIN_PWR  = 21;

// Display dimensions
const int DISPLAY_WIDTH = 800;
const int DISPLAY_HEIGHT = 480;

// Image handling - BMP files are larger (uncompressed)
const size_t MAX_IMAGE_SIZE = 1200000; // 1.2MB for BMP
uint8_t* imageBuffer = nullptr;

// Dithering buffer for error diffusion
int16_t* errorBuffer = nullptr;

// RTC memory
RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR time_t lastUpdate = 0;
RTC_DATA_ATTR bool firstBoot = true;

GxEPD2_3C<GxEPD2_750c_Z08, GxEPD2_750c_Z08::HEIGHT / 8> display(GxEPD2_750c_Z08(PIN_CS, PIN_DC, PIN_RST, PIN_BUSY));

// Forward declarations
void showError(const char* message);
void goToSleep();
bool downloadAndDisplayCalendar();

// BMP Header structures
#pragma pack(push, 1)
struct BMPHeader {
  uint16_t signature;
  uint32_t fileSize;
  uint16_t reserved1;
  uint16_t reserved2;
  uint32_t dataOffset;
};

struct BMPInfoHeader {
  uint32_t headerSize;
  int32_t width;
  int32_t height;
  uint16_t planes;
  uint16_t bitsPerPixel;
  uint32_t compression;
  uint32_t imageSize;
  int32_t xPixelsPerMeter;
  int32_t yPixelsPerMeter;
  uint32_t colorsUsed;
  uint32_t colorsImportant;
};
#pragma pack(pop)

// Color distance function for 3-color e-ink
struct EinkColor {
  uint8_t r, g, b;
  uint16_t code;
};

const EinkColor einkPalette[3] = {
  {255, 255, 255, GxEPD_WHITE},  // White
  {0, 0, 0, GxEPD_BLACK},         // Black
  {255, 0, 0, GxEPD_RED}          // Red
};

// Find closest color in palette and return error
uint16_t findClosestColor(uint8_t r, uint8_t g, uint8_t b, int16_t* errorR, int16_t* errorG, int16_t* errorB) {
  int minDistance = 999999;
  uint16_t closestColor = GxEPD_WHITE;
  uint8_t closestR = 255, closestG = 255, closestB = 255;
  
  for (int i = 0; i < 3; i++) {
    int dr = r - einkPalette[i].r;
    int dg = g - einkPalette[i].g;
    int db = b - einkPalette[i].b;
    int distance = dr*dr + dg*dg + db*db;
    
    if (distance < minDistance) {
      minDistance = distance;
      closestColor = einkPalette[i].code;
      closestR = einkPalette[i].r;
      closestG = einkPalette[i].g;
      closestB = einkPalette[i].b;
    }
  }
  
  // Calculate error
  *errorR = r - closestR;
  *errorG = g - closestG;
  *errorB = b - closestB;
  
  return closestColor;
}

void setup() {
  Serial.begin(115200);
  delay(3000);
  
  Serial.println("\n\n=== ESP32-S3 Calendar Display Starting ===");
  Serial.printf("Display: DEPG0750 (%dx%d) with Floyd-Steinberg dithering\n", DISPLAY_WIDTH, DISPLAY_HEIGHT);
  
  // Disable watchdog
  esp_task_wdt_deinit();
  
  ++bootCount;
  Serial.printf("Boot #%d\n", bootCount);
  
  // Check PSRAM
  if (!psramFound()) {
    Serial.println("ERROR: PSRAM not found!");
    showError("PSRAM Error");
    goToSleep();
    return;
  }
  Serial.printf("PSRAM OK: %d bytes, Free: %d bytes\n", ESP.getPsramSize(), ESP.getFreePsram());
  Serial.printf("Free heap: %u bytes\n", ESP.getFreeHeap());
  
  // Initialize display power
  pinMode(PIN_PWR, OUTPUT);
  digitalWrite(PIN_PWR, HIGH);
  delay(500);
  
  // Check wake up reason
  esp_sleep_wakeup_cause_t wakeupReason = esp_sleep_get_wakeup_cause();
  
  // If woken by button (EXT0), it's a manual update
  bool manualUpdate = (wakeupReason == ESP_SLEEP_WAKEUP_EXT0);
  
  Serial.printf("Wakeup reason: %d, Manual update: %s\n", wakeupReason, manualUpdate ? "YES" : "NO");
  
  if (firstBoot || manualUpdate || shouldCheckForUpdate()) {
    if (connectToWiFi()) {
      Serial.printf("Connected, free heap: %u, free PSRAM: %u\n", ESP.getFreeHeap(), ESP.getFreePsram());
      
      if (downloadAndDisplayCalendar()) {
        lastUpdate = time(nullptr);
        firstBoot = false;
        Serial.println("=== SUCCESS: Calendar displayed! ===");
      } else {
        Serial.println("=== FAILED: Calendar update failed! ===");
      }
      
      WiFi.disconnect(true);
      WiFi.mode(WIFI_OFF);
      delay(1000);
    } else {
      showError("WiFi Failed");
    }
  } else {
    Serial.println("No update needed, going back to sleep");
  }
  
  // Power off display to save energy
  digitalWrite(PIN_PWR, LOW);
  
  Serial.println("Setup complete, entering sleep mode");
  Serial.flush();
  delay(1000);
  
  goToSleep();
}

void loop() {}

bool shouldCheckForUpdate() {
  if (firstBoot) return true;
  
  time_t now = time(nullptr);
  if (now < 1000000) return true;
  
  if (now - lastUpdate > (BACKUP_CHECK_HOURS * 3600)) {
    Serial.printf("Backup check needed. Last update: %ld, now: %ld\n", lastUpdate, now);
    return true;
  }
  
  struct tm* timeinfo = localtime(&now);
  int hour = timeinfo->tm_hour;
  int minute = timeinfo->tm_min;
  
  if ((hour == 23 && minute >= 30) || hour == 0 || (hour == 1 && minute <= 30)) {
    Serial.printf("Midnight window check at %02d:%02d\n", hour, minute);
    return true;
  }
  
  return false;
}

bool connectToWiFi() {
  Serial.println("Connecting to WiFi...");
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nWiFi connected! IP: %s\n", WiFi.localIP().toString().c_str());
    
    configTime(0, 0, "pool.ntp.org");
    setenv("TZ", TIMEZONE, 1);
    tzset();
    
    time_t now = time(nullptr);
    int timeouts = 0;
    while (now < 1000000 && timeouts < 10) {
      delay(1000);
      now = time(nullptr);
      timeouts++;
      Serial.print("T");
    }
    Serial.printf("\nTime synced: %s", ctime(&now));
    return true;
  } else {
    Serial.println("\nWiFi connection failed!");
    return false;
  }
}

bool downloadAndDisplayCalendar() {
  Serial.println("\n=== Starting Calendar Download ===");
  
  // Check server info
  HTTPClient http;
  http.setTimeout(15000);
  http.begin(String(SERVER_URL) + "/info");
  
  Serial.println("Checking server status...");
  int httpCode = http.GET();
  
  if (httpCode != 200) {
    Serial.printf("Info request failed: %d\n", httpCode);
    http.end();
    showError("Server Error");
    return false;
  }
  
  String payload = http.getString();
  http.end();
  
  Serial.printf("Server info: %s\n", payload.c_str());
  
  DynamicJsonDocument doc(512);
  DeserializationError error = deserializeJson(doc, payload);
  
  if (error) {
    Serial.printf("JSON parse failed: %s\n", error.c_str());
    showError("JSON Error");
    return false;
  }
  
  bool calendarAvailable = doc["calendar_available"];
  
  if (!calendarAvailable) {
    Serial.println("Calendar not ready on server");
    showError("Not Ready");
    return false;
  }
  
  Serial.printf("Free PSRAM before download: %u bytes\n", ESP.getFreePsram());
  Serial.printf("Free heap before download: %u bytes\n", ESP.getFreeHeap());
  
  // Download BMP file
  http.begin(String(SERVER_URL) + "/calendar.png");
  http.setTimeout(120000);
  
  Serial.println("Requesting calendar image (BMP format)...");
  httpCode = http.GET();
  
  if (httpCode != 200) {
    Serial.printf("Image download failed: %d\n", httpCode);
    http.end();
    showError("Download Failed");
    return false;
  }
  
  int fileSize = http.getSize();
  Serial.printf("Calendar file size from server: %d bytes\n", fileSize);
  
  if (fileSize <= 0 || fileSize > MAX_IMAGE_SIZE) {
    Serial.printf("Invalid file size: %d\n", fileSize);
    http.end();
    showError(fileSize > MAX_IMAGE_SIZE ? "File Too Large" : "Invalid Size");
    return false;
  }
  
  // Allocate image buffer in PSRAM
  Serial.printf("Allocating %d bytes in PSRAM...\n", fileSize);
  imageBuffer = (uint8_t*)ps_malloc(fileSize);
  
  if (!imageBuffer) {
    Serial.printf("Failed to allocate image buffer\n");
    http.end();
    showError("Memory Error");
    return false;
  }
  
  // Allocate error diffusion buffer (2 rows * 3 channels)
  errorBuffer = (int16_t*)ps_malloc(DISPLAY_WIDTH * 2 * 3 * sizeof(int16_t));
  if (!errorBuffer) {
    Serial.println("Failed to allocate error buffer");
    free(imageBuffer);
    imageBuffer = nullptr;
    http.end();
    showError("Memory Error");
    return false;
  }
  memset(errorBuffer, 0, DISPLAY_WIDTH * 2 * 3 * sizeof(int16_t));
  
  Serial.printf("Allocated buffers successfully\n");
  
  // Read image data
  WiFiClient* stream = http.getStreamPtr();
  uint32_t bytesRead = 0;
  uint32_t lastProgress = 0;
  
  Serial.println("Downloading BMP image...");
  unsigned long downloadStart = millis();
  
  while (http.connected() && bytesRead < fileSize) {
    if (millis() - downloadStart > 120000) {
      Serial.println("Download timeout!");
      break;
    }
    
    size_t available = stream->available();
    if (available) {
      size_t toRead = min(available, (size_t)(fileSize - bytesRead));
      size_t actualRead = stream->readBytes(imageBuffer + bytesRead, toRead);
      
      if (actualRead > 0) {
        bytesRead += actualRead;
        
        if (bytesRead - lastProgress >= 50000 || bytesRead == fileSize) {
          Serial.printf("Downloaded: %u / %d bytes (%.1f%%)\n", 
                        bytesRead, fileSize, (bytesRead * 100.0) / fileSize);
          lastProgress = bytesRead;
        }
      }
    } else {
      delay(10);
    }
    yield();
  }
  
  http.end();
  
  if (bytesRead < fileSize) {
    Serial.printf("Incomplete download\n");
    free(imageBuffer);
    free(errorBuffer);
    imageBuffer = nullptr;
    errorBuffer = nullptr;
    showError("Download Incomplete");
    return false;
  }
  
  // Parse BMP header
  Serial.println("\n=== BMP File Analysis ===");
  
  BMPHeader* bmpHeader = (BMPHeader*)imageBuffer;
  BMPInfoHeader* infoHeader = (BMPInfoHeader*)(imageBuffer + sizeof(BMPHeader));
  
  Serial.printf("BMP signature: 0x%04X\n", bmpHeader->signature);
  
  if (bmpHeader->signature != 0x4D42) {
    Serial.println("ERROR: Not a valid BMP file!");
    free(imageBuffer);
    free(errorBuffer);
    imageBuffer = nullptr;
    errorBuffer = nullptr;
    showError("Invalid BMP");
    return false;
  }
  
  Serial.printf("BMP dimensions: %dx%d\n", infoHeader->width, abs(infoHeader->height));
  Serial.printf("Bits per pixel: %d\n", infoHeader->bitsPerPixel);
  
  if (infoHeader->width != DISPLAY_WIDTH || abs(infoHeader->height) != DISPLAY_HEIGHT) {
    Serial.printf("ERROR: Wrong dimensions\n");
    free(imageBuffer);
    free(errorBuffer);
    imageBuffer = nullptr;
    errorBuffer = nullptr;
    showError("Wrong Size");
    return false;
  }
  
  if (infoHeader->bitsPerPixel != 24) {
    Serial.printf("ERROR: Wrong bit depth\n");
    free(imageBuffer);
    free(errorBuffer);
    imageBuffer = nullptr;
    errorBuffer = nullptr;
    showError("Wrong Format");
    return false;
  }
  
  // Initialize display
  Serial.println("Initializing display...");
  display.init(115200, true, 2);
  display.setFullWindow();
  
  // Parse BMP data
  uint8_t* pixelData = imageBuffer + bmpHeader->dataOffset;
  int rowSize = ((infoHeader->width * 3 + 3) / 4) * 4;
  bool bottomUp = infoHeader->height > 0;
  
  Serial.println("Drawing BMP with Floyd-Steinberg dithering...");
  
  do {
    // Reset error buffer for each page
    memset(errorBuffer, 0, DISPLAY_WIDTH * 2 * 3 * sizeof(int16_t));
    
    for (int y = 0; y < DISPLAY_HEIGHT; y++) {
      int srcY = bottomUp ? (DISPLAY_HEIGHT - 1 - y) : y;
      uint8_t* row = pixelData + (srcY * rowSize);
      
      // Current and next row in error buffer
      int16_t* currError = errorBuffer + ((y % 2) * DISPLAY_WIDTH * 3);
      int16_t* nextError = errorBuffer + (((y + 1) % 2) * DISPLAY_WIDTH * 3);
      
      for (int x = 0; x < DISPLAY_WIDTH; x++) {
        // Get original color (BGR format)
        uint8_t b = row[x * 3];
        uint8_t g = row[x * 3 + 1];
        uint8_t r = row[x * 3 + 2];
        
        // Add accumulated error from previous pixels
        int16_t newR = constrain(r + currError[x * 3 + 0], 0, 255);
        int16_t newG = constrain(g + currError[x * 3 + 1], 0, 255);
        int16_t newB = constrain(b + currError[x * 3 + 2], 0, 255);
        
        // Find closest color and get quantization error
        int16_t errorR, errorG, errorB;
        uint16_t color = findClosestColor(newR, newG, newB, &errorR, &errorG, &errorB);
        
        // Draw pixel
        display.drawPixel(x, y, color);
        
        // Distribute error to neighboring pixels (Floyd-Steinberg)
        if (x + 1 < DISPLAY_WIDTH) {
          currError[(x + 1) * 3 + 0] += errorR * 7 / 16;
          currError[(x + 1) * 3 + 1] += errorG * 7 / 16;
          currError[(x + 1) * 3 + 2] += errorB * 7 / 16;
        }
        
        if (y + 1 < DISPLAY_HEIGHT) {
          if (x > 0) {
            nextError[(x - 1) * 3 + 0] += errorR * 3 / 16;
            nextError[(x - 1) * 3 + 1] += errorG * 3 / 16;
            nextError[(x - 1) * 3 + 2] += errorB * 3 / 16;
          }
          
          nextError[x * 3 + 0] += errorR * 5 / 16;
          nextError[x * 3 + 1] += errorG * 5 / 16;
          nextError[x * 3 + 2] += errorB * 5 / 16;
          
          if (x + 1 < DISPLAY_WIDTH) {
            nextError[(x + 1) * 3 + 0] += errorR * 1 / 16;
            nextError[(x + 1) * 3 + 1] += errorG * 1 / 16;
            nextError[(x + 1) * 3 + 2] += errorB * 1 / 16;
          }
        }
      }
      
      // Clear current row errors for next iteration
      memset(currError, 0, DISPLAY_WIDTH * 3 * sizeof(int16_t));
      
      if (y % 50 == 0 && y > 0) {
        Serial.printf("Drawing: %d / %d lines (%.1f%%)\n", y, DISPLAY_HEIGHT, (y * 100.0) / DISPLAY_HEIGHT);
      }
    }
    Serial.println("Updating display...");
  } while (display.nextPage());
  
  Serial.println("Display refresh complete!");
  
  // Clean up
  free(imageBuffer);
  free(errorBuffer);
  imageBuffer = nullptr;
  errorBuffer = nullptr;
  
  Serial.printf("Free PSRAM after cleanup: %u bytes\n", ESP.getFreePsram());
  Serial.printf("Free heap after cleanup: %u bytes\n", ESP.getFreeHeap());
  
  Serial.println("\n=== Calendar image displayed successfully! ===");
  return true;
}

void showError(const char* message) {
  Serial.printf("Displaying error: %s\n", message);
  
  pinMode(PIN_PWR, OUTPUT);
  digitalWrite(PIN_PWR, HIGH);
  delay(500);
  
  display.init(115200, true, 2);
  display.setFullWindow();
  display.firstPage();
  
  do {
    display.fillScreen(GxEPD_WHITE);
    display.setTextColor(GxEPD_BLACK);
    display.setTextSize(2);
    display.setCursor(200, 200);
    display.print("Error");
    
    display.setTextColor(GxEPD_RED);
    display.setTextSize(1);
    display.setCursor(200, 240);
    display.print(message);
    
    display.setCursor(200, 270);
    display.printf("Boot: %d", bootCount);
  } while (display.nextPage());
  
  Serial.println("Error displayed on screen");
}

void goToSleep() {
  Serial.println("Entering deep sleep...");
  Serial.flush();
  delay(500);
  
  uint64_t sleepTime = getNextWakeupInterval();
  Serial.printf("Sleep duration: %llu seconds (%.1f hours)\n", sleepTime, sleepTime / 3600.0);
  
  // Enable timer wakeup
  esp_sleep_enable_timer_wakeup(sleepTime * 1000000ULL);
  
  // Enable manual wakeup via button press (GPIO 0)
  esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0);
  
  Serial.println("Good night!");
  Serial.flush();
  delay(100);
  
  esp_deep_sleep_start();
}

uint64_t getNextWakeupInterval() {
  time_t now = time(nullptr);
  
  // If time not synced, use backup interval
  if (now < 1000000) {
    return BACKUP_CHECK_HOURS * 3600;
  }
  
  struct tm* timeinfo = localtime(&now);
  int currentHour = timeinfo->tm_hour;
  int currentMinute = timeinfo->tm_min;
  
  int secondsUntilMidnight = 0;
  
  // Calculate seconds until 23:30 (or next day's 23:30 if already past)
  if (currentHour < 23 || (currentHour == 23 && currentMinute < 30)) {
    // Today's 23:30
    secondsUntilMidnight = (23 - currentHour) * 3600 + (30 - currentMinute) * 60 - timeinfo->tm_sec;
  } else {
    // Tomorrow's 23:30
    int hoursUntilTomorrow = (24 - currentHour - 1) + 23;
    int minutesUntilTomorrow = (60 - currentMinute) + 30;
    secondsUntilMidnight = hoursUntilTomorrow * 3600 + minutesUntilTomorrow * 60 - timeinfo->tm_sec;
  }
  
  // Use the shorter of: time until midnight window or backup check interval
  return min((uint64_t)secondsUntilMidnight, (uint64_t)(BACKUP_CHECK_HOURS * 3600));
}
