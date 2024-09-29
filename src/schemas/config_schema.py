from src.schemas.constants import load_common_defs
from src.utils.constants import SUPPORTED_PROCESSOR_NAMES

CONFIG_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/Udayraj123/OMRChecker/tree/master/src/schemas/config-schema.json",
    "$def": {
        # The common definitions go here
        **load_common_defs(["two_positive_integers"]),
    },
    "title": "Config Schema",
    "description": "OMRChecker config schema for custom tuning",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "thresholding": {
            "description": "The values used in the core algorithm of OMRChecker",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                # TODO: rename all of these variables for better usability
                "MIN_GAP_TWO_BUBBLES": {
                    "description": "Minimum difference between all mean values of the bubbles. Used for local thresholding of 2 or 1 bubbles",
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 100,
                },
                "MIN_JUMP": {
                    "description": "Minimum difference between consecutive elements to be consider as a jump in a sorted array of mean values of the bubbles",
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 100,
                },
                "MIN_JUMP_STD": {
                    "description": "The MIN_JUMP for the standard deviation plot",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                },
                "MIN_JUMP_SURPLUS_FOR_GLOBAL_FALLBACK": {
                    "description": "This value is added to jump value, underconfident bubbles fallback to global_threshold_for_template",
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 20,
                },
                "GLOBAL_THRESHOLD_MARGIN": {
                    "description": 'This value determines if the calculated global threshold is "too close" to lower bubbles in confidence metrics ',
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 20,
                },
                "JUMP_DELTA": {
                    "description": "Note: JUMP_DELTA is deprecated, used only in plots currently to determine a stricter threshold",
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 100,
                },
                "JUMP_DELTA_STD": {
                    "description": "JUMP_DELTA_STD is the minimum delta to be considered as a jump in the std plot",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                },
                "CONFIDENT_JUMP_SURPLUS_FOR_DISPARITY": {
                    "description": "This value is added to jump value to distinguish safe detections vs underconfident detections",
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                },
                "GLOBAL_PAGE_THRESHOLD": {
                    "description": "This option decides the starting value to use before applying local outlier threshold",
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                },
                "GLOBAL_PAGE_THRESHOLD_STD": {
                    "description": "This option decides the starting value to use for standard deviation threshold which determines outliers",
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 60,
                },
                "GAMMA_LOW": {
                    "description": "Used in the CropOnDotLines processor to create a darker image for enhanced line detection (darker boxes)",
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
            },
        },
        "outputs": {
            "description": "The configuration related to the outputs generated by OMRChecker",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "display_image_dimensions": {
                    "$ref": "#/$def/two_positive_integers",
                    "description": "The dimensions (width, height) for images displayed during the execution",
                },
                "show_logs_by_type": {
                    "description": "The toggles for enabling logs per level",
                    "type": "object",
                    "properties": {
                        "critical": {"type": "boolean"},
                        "error": {"type": "boolean"},
                        "warning": {"type": "boolean"},
                        "info": {"type": "boolean"},
                        "debug": {"type": "boolean"},
                    },
                },
                "show_image_level": {
                    "description": "The toggle level for showing debug images (higher means more debug images)",
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 6,
                },
                "save_image_level": {
                    "description": "The toggle level for saving debug images (higher means more debug images)",
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 6,
                },
                "colored_outputs_enabled": {
                    "description": "This option shows colored outputs while taking a small toll on the processing speeds",
                    "type": "boolean",
                },
                "save_detections": {
                    "description": "This option saves the detection outputs while taking a small toll on the processing speeds",
                    "type": "boolean",
                },
                "save_image_metrics": {
                    "description": "This option exports the confidence metrics etc related to the images. These can be later used for deeper analysis/visualizations",
                    "type": "boolean",
                },
                "filter_out_multimarked_files": {
                    "description": "This option moves files having multi-marked responses into a separate folder for manual checking, skipping evaluation",
                    "type": "boolean",
                },
                "show_preprocessors_diff": {
                    "description": "This option shows a preview of the processed image for every preprocessor. Also granular at preprocessor level using a map",
                    "oneOf": [
                        {
                            "type": "object",
                            "patternProperties": {
                                f"^({'|'.join(SUPPORTED_PROCESSOR_NAMES)})$": {
                                    "type": "boolean"
                                }
                            },
                        },
                        {"type": "boolean"},
                    ],
                },
            },
        },
    },
}
