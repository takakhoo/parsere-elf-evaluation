#include <stdlib.h>
#include <string.h>

#include <curl/curl.h>

#define MAX_URL_LEN (32768)
static char url_string[MAX_URL_LEN + 1];

int main(void) {
    fread(url_string, 1, MAX_URL_LEN, stdin);

    CURLU *const parsed_url = curl_url();
    CURLUcode const rc = curl_url_set(parsed_url, CURLUPART_URL, url_string, CURLU_GUESS_SCHEME | CURLU_NON_SUPPORT_SCHEME);

    return rc;
}
