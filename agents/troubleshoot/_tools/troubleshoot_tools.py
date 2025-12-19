TROUBLESHOOT_TOOLS_SCHEMA = [
    {
        "type": "function",
        "name": "get_robot_status",
        "description": "Retrieve real-time sensor data, battery health, and error logs for a robot.",
        "parameters": {
            "type": "object",
            "properties": {
                "serial_number": {
                    "type": "string",
                    "description": "The unique serial number of the robot vacuum."
                }
            },
            "required": ["serial_number"]
        }
    },
    {
        "type": "function",
        "name": "run_remote_diag",
        "description": "Triggers a remote self-test of the robot's hardware components.",
        "parameters": {
            "type": "object",
            "properties": {
                "serial_number": {
                    "type": "string",
                    "description": "The unique serial number of the robot vacuum."
                }
            },
            "required": ["serial_number"]
        }
    },
    {
        "type": "function",
        "name": "reset_firmware",
        "description": "Performs a factory reset and reinstall of the latest firmware. Deletes maps.",
        "parameters": {
            "type": "object",
            "properties": {
                "serial_number": {
                    "type": "string",
                    "description": "The unique serial number of the robot vacuum."
                }
            },
            "required": ["serial_number"]
        }
    },
    {
        "type": "function",
        "name": "schedule_repair",
        "description": "Logs a hardware failure and schedules a technician visit.",
        "parameters": {
            "type": "object",
            "properties": {
                "serial_number": {
                    "type": "string",
                    "description": "The unique serial number of the robot vacuum."
                },
                "part_needed": {
                    "type": "string",
                    "description": "The specific component requiring replacement (e.g., Lidar, Wheel Motor)."
                },
                "address": {
                    "type": "string",
                    "description": "The customer's service address."
                }
            },
            "required": ["serial_number", "part_needed", "address"]
        }
    }
]

def get_robot_status(serial_number: str):
    """
    Returns diagnostic data for the robot.
    Mock data — returns same diagnostic state regardless of serial number.
    """
    diagnostics = [
        {
            "serial_number": serial_number,
            "model": "SmartClean Pro-X",
            "owner": "John Doe",
            "status_report": {
                "battery_level": 15,
                "firmware_version": "v2.1.0",
                "last_error_code": "E102",
                "component_health": [
                    {"component": "Lidar Sensor", "status": "OK"},
                    {"component": "Left Wheel Motor", "status": "STALLED"},
                    {"component": "Suction Fan", "status": "OK"},
                    {"component": "Main Brush", "status": "OK"},
                ],
                "error_history": ["E102: Wheel Motor Obstruction", "E004: Battery Low"]
            }
        }
    ]
    return diagnostics

def run_remote_diag(serial_number: str):
    """
    Simulates a remote hardware test.
    """
    # Mock logic to 'detect' a fault
    return f"Remote diagnostics for {serial_number} completed. Result: Detected high resistance in Left Wheel Motor. Suction and Lidar tests passed."

def reset_firmware(serial_number: str):
    """
    Simulates a factory reset. 
    In the prompt, the agent must ask for user consent before calling this.
    """
    return f"Factory reset initiated for {serial_number}. Custom maps and schedules have been cleared. Robot is now on firmware v2.1.1."

def schedule_repair(serial_number: str, part_needed: str, address: str):
    """
    Simulates scheduling a technician.
    """
    if not part_needed or not address:
        return "Error: Missing part identification or service address."
    
    return f"Repair ticket created for {serial_number}. A technician will arrive at {address} with a replacement {part_needed} within 48 hours."

TROUBLESHOOT_TOOL_MAP = {
    "get_robot_status": get_robot_status,
    "run_remote_diag": run_remote_diag,
    "reset_firmware": reset_firmware,
    "schedule_repair": schedule_repair
}