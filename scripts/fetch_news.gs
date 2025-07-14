function fetchNews() {
  try {
    var aiUrl = "https://news.google.com/rss/search?q=artificial+intelligence+when:1d";
    var econUrl = "https://news.google.com/rss/search?q=global+economy+when:1d";
    
    var aiResponse = UrlFetchApp.fetch(aiUrl);
    var aiXml = XmlService.parse(aiResponse.getContentText());
    var aiItems = aiXml.getRootElement().getChildren('channel')[0].getChildren('item');
    var aiNews = {
      title: aiItems[0].getChild('title').getText(),
      summary: aiItems[0].getChild('description').getText().substring(0, 100) + "..."
    };
    
    var econResponse = UrlFetchApp.fetch(econUrl);
    var econXml = XmlService.parse(econResponse.getContentText());
    var econItems = econXml.getRootElement().getChildren('channel')[0].getChildren('item');
    var econNews = {
      title: econItems[0].getChild('title').getText(),
      summary: econItems[0].getChild('description').getText().substring(0, 100) + "..."
    };
    
    var sheet = SpreadsheetApp.openById('YOUR_SHEET_ID').getSheetByName('News');
    sheet.clear();
    sheet.appendRow(['AI', aiNews.title, aiNews.summary]);
    sheet.appendRow(['Economic', econNews.title, econNews.summary]);
    
    var news = { 'ai': aiNews, 'economic': econNews };
    var blob = Utilities.newBlob(JSON.stringify(news), 'application/json', 'news.json');
    DriveApp.createFile(blob);
    
    Logger.log('News fetched successfully');
    return news;
  } catch (e) {
    Logger.log('Error fetching news: ' + e);
    throw e;
  }
}

function doGet() {
  var news = fetchNews();
  return ContentService.createTextOutput(JSON.stringify(news))
    .setMimeType(ContentService.MimeType.JSON);
}
