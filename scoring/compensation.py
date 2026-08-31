from typing import Dict, Any, List, Tuple

def get_commission_rate(closed_clients_count: int) -> float:
    """
    Returns commission rate as a float (0.35, 0.40, 0.45) based on monthly closed clients:
    - 1 client -> 35%
    - 2-4 clients -> 40%
    - 5+ clients -> 45%
    """
    if closed_clients_count >= 5:
        return 0.45
    elif closed_clients_count >= 2:
        return 0.40
    elif closed_clients_count == 1:
        return 0.35
    else:
        return 0.35

def get_commission_percentage_str(closed_clients_count: int) -> str:
    """Returns '35%', '40%', or '45%'."""
    rate = get_commission_rate(closed_clients_count)
    return f"{int(rate * 100)}%"

def calculate_monthly_commission(total_sales_revenue: float, closed_clients_count: int) -> float:
    """
    Calculates monthly commission.
    The higher percentage applies to ALL sales in the current calendar month.
    """
    rate = get_commission_rate(closed_clients_count)
    return round(total_sales_revenue * rate, 2)

def evaluate_activity_bonus_status(weekly_contacts_count: int) -> bool:
    """
    Rule: 40+ confirmed cold contacts in a working week activates the bonus for the NEXT week.
    """
    return weekly_contacts_count >= 40

def calculate_activity_bonus(clients_closed_in_bonus_week: int, is_bonus_active: bool) -> float:
    """
    Rule: +1 000 UAH for EACH closed client during the active bonus week.
    If bonus is not active, bonus = 0 UAH.
    """
    if not is_bonus_active or clients_closed_in_bonus_week <= 0:
        return 0.0
    return float(clients_closed_in_bonus_week * 1000)

def calculate_total_earnings(
    total_sales_revenue: float,
    closed_clients_count: int,
    clients_closed_in_bonus_week: int = 0,
    is_activity_bonus_active: bool = False,
    is_best_manager_of_month: bool = False,
    team_sales_revenue: float = 0.0,
    is_team_lead: bool = False
) -> Dict[str, Any]:
    """
    Comprehensive manager compensation breakdown:
    - Base commission (35% / 40% / 45% for all sales this month)
    - Activity bonus (+1000 UAH per closed client during active bonus weeks)
    - Best manager of month bonus (+5000 UAH)
    - Team Lead bonus (+5% from team sales)
    """
    commission_rate = get_commission_rate(closed_clients_count)
    commission_amount = round(total_sales_revenue * commission_rate, 2)
    activity_bonus_amount = calculate_activity_bonus(clients_closed_in_bonus_week, is_activity_bonus_active)
    
    best_manager_bonus = 5000.0 if is_best_manager_of_month else 0.0
    team_lead_bonus = round(team_sales_revenue * 0.05, 2) if is_team_lead else 0.0

    total_earnings = round(
        commission_amount + activity_bonus_amount + best_manager_bonus + team_lead_bonus,
        2
    )

    return {
        "commission_rate": commission_rate,
        "commission_rate_str": f"{int(commission_rate * 100)}%",
        "commission_amount": commission_amount,
        "activity_bonus_amount": activity_bonus_amount,
        "best_manager_bonus": best_manager_bonus,
        "team_lead_bonus": team_lead_bonus,
        "total_earnings": total_earnings
    }
