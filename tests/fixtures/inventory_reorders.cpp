#include "inventory.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

Inventory::Inventory() : items_(nullptr), size_(0) {
    items_ = new Item*[MAX_ITEMS];
    for (int i = 0; i < MAX_ITEMS; i++) {
        items_[i] = nullptr;
    }
}

Inventory::~Inventory() {
    for (int i = 0; i < size_; i++) {
        delete items_[i];
    }
    delete[] items_;
}

bool Inventory::add(const char* sku, const char* name, int quantity, double unitPrice) {
    if (sku == nullptr || name == nullptr || quantity < 0 || unitPrice < 0) {
        return false;
    }
    if (size_ >= MAX_ITEMS || find(sku) != nullptr) {
        return false;
    }
    Item* item = new Item;
    item->sku = sku;
    item->name = name;
    item->quantity = quantity;
    item->unitPrice = unitPrice;
    items_[size_++] = item;
    return true;
}

Item* Inventory::find(const std::string& sku) const {
    for (int i = 0; i < size_; i++) {
        if (items_[i]->sku == sku) {
            return items_[i];
        }
    }
    return nullptr;
}

bool Inventory::remove(const std::string& sku) {
    for (int i = 0; i < size_; i++) {
        if (items_[i]->sku == sku) {
            delete items_[i];
            items_[i] = items_[--size_];
            items_[size_] = nullptr;
            return true;
        }
    }
    return false;
}

int Inventory::count() const {
    return size_;
}

double Inventory::totalValue() const {
    double total = 0;
    for (int i = 0; i < size_; i++) {
        total += static_cast<double>(items_[i]->quantity) * items_[i]->unitPrice;
    }
    return total;
}

NameList Inventory::lowStock() const {
    NameList names;
    for (int i = 0; i < size_; i++) {
        if (items_[i]->quantity < LOW_STOCK_THRESHOLD) {
            names.push_back(items_[i]->name);
        }
    }
    return names;
}

char* Inventory::report() const {
    std::string text;
    char line[64];
    for (int i = 0; i < size_; i++) {
        std::snprintf(line, sizeof line, "%s x%d\n", items_[i]->sku.c_str(),
                      items_[i]->quantity);
        text += line;
    }
    // The header's contract is a malloc'd buffer the caller frees, so keep that.
    char* out = static_cast<char*>(std::malloc(text.size() + 1));
    std::memcpy(out, text.c_str(), text.size() + 1);
    return out;
}
