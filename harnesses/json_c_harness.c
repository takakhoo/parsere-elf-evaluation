#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#include <json.h>

#define MAX_INPUT_LEN (32768)
static char input[MAX_INPUT_LEN + 1];

int main(void) {
    fread(input, 1, MAX_INPUT_LEN, stdin);

    return json_tokener_parse(input) == NULL;
}
