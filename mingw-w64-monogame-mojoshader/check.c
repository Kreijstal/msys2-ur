/* MonoGame's mojoshader exports only MOJOSHADER_parse, parseExpression and
 * runPreshader (mgfxc only calls MOJOSHADER_parse).
 * Translate a hand-assembled ps_2_0 shader (mov oC0, c0) and a vs_2_0
 * shader (dp4 oPos.x, v0, c0 ...) to GLSL the way MonoGame's mgfxc does. */
#include <stdio.h>
#include <string.h>
#include "mojoshader.h"

static int run(const char *what, const unsigned int *tok, unsigned len, const char *expect)
{
    const MOJOSHADER_parseData *pd = MOJOSHADER_parse(MOJOSHADER_PROFILE_GLSL,
        (const unsigned char *)tok, len, NULL, 0, NULL, 0, NULL, NULL, NULL);
    int ok = pd && pd->error_count == 0 && pd->output && strstr(pd->output, expect);
    printf("%s: errors=%d uniforms=%d\n%s\n", what, pd ? pd->error_count : -1,
        pd ? pd->uniform_count : -1, pd && pd->output ? pd->output : (pd && pd->error_count ? pd->errors[0].error : ""));
    return ok;
}

int main(void)
{
    static const unsigned int ps[] = {
        0xFFFF0200,             /* ps_2_0 */
        0x02000001, 0x800F0800, 0xA0E40000, /* mov oC0, c0 */
        0x0000FFFF };
    static const unsigned int vs[] = {
        0xFFFE0200,             /* vs_2_0 */
        0x0200001F, 0x80000000, 0x900F0000, /* dcl_position v0 */
        0x03000009, 0xC0010000, 0x90E40000, 0xA0E40000, /* dp4 oPos.x, v0, c0 */
        0x03000009, 0xC0020000, 0x90E40000, 0xA0E40001, /* dp4 oPos.y, v0, c1 */
        0x03000009, 0xC0040000, 0x90E40000, 0xA0E40002, /* dp4 oPos.z, v0, c2 */
        0x03000009, 0xC0080000, 0x90E40000, 0xA0E40003, /* dp4 oPos.w, v0, c3 */
        0x0000FFFF };
    if (!run("ps_2_0", ps, sizeof ps, "gl_FragColor")) return 1;
    if (!run("vs_2_0", vs, sizeof vs, "gl_Position")) return 1;
    puts("mojoshader GLSL translation OK");
    return 0;
}
