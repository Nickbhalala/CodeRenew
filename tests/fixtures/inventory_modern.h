// A small inventory module written in pre-C++11 style on purpose.
// It is the demo input for CodeRenew.
#ifndef INVENTORY_H
#define INVENTORY_H

#include <string>
#include <vector>

constexpr int MAX_ITEMS = 100;
constexpr int LOW_STOCK_THRESHOLD = 5;

using NameList = std::vector<std::string>;

struct Item {
    std::string sku;
    std::string name;
    int quantity;
    double unitPrice;
};

class Inventory {
public:
    Inventory();
    ~Inventory();

    bool add(const char* sku, const char* name, int quantity, double unitPrice);
    Item* find(const std::string& sku) const;
    bool remove(const std::string& sku);
    int count() const;
    double totalValue() const;
    NameList lowStock() const;
    // Returns a malloc'd C string; the caller must free() it.
    char* report() const;

private:
    Item** items_;
    int size_;

    Inventory(const Inventory&) = delete;
    Inventory& operator=(const Inventory&) = delete;
};

#endif
