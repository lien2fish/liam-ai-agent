import os

from PIL import ImageCms

ENV_VAR = "PRINT_CMYK_ICC"
KNOWN_CMYK_PROFILES = (
    "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc",
    "/usr/share/color/icc/colord/FOGRA39L_coated.icc",
    "/usr/share/color/icc/colord/SWOP.icc",
    "/usr/share/color/icc/ghostscript/default_cmyk.icc",
    "/usr/share/color/icc/ghostscript/ps_cmyk.icc",
)


class ToolError(Exception):
    pass


def find_cmyk_profile(explicit=None):
    env_value = os.environ.get(ENV_VAR)
    candidates = (
        [explicit]
        if explicit
        else [env_value] if env_value else list(KNOWN_CMYK_PROFILES)
    )
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            profile = ImageCms.getOpenProfile(path)
        except (OSError, ImageCms.PyCMSError) as exc:
            raise ToolError(f"Cannot read ICC profile {path}: {exc}")
        if profile.profile.xcolor_space.strip() != "CMYK":
            raise ToolError(f"{path} is not a CMYK profile.")
        return path, profile
    if explicit:
        raise ToolError(f"ICC profile not found: {explicit}")
    raise ToolError(
        "No CMYK ICC profile found. Ask the print shop for theirs and pass --icc "
        f"(or set {ENV_VAR}). If the shop confirms it accepts RGB, rebuild with "
        "--color rgb. If it only takes CMYK and has no profile, download a standard "
        "one yourself, for example from eci.org. An unprofiled conversion is refused "
        "on purpose: it misrepresents color."
    )


def profile_label(profile):
    try:
        return ImageCms.getProfileDescription(profile).strip()
    except ImageCms.PyCMSError:
        return "unknown profile"
