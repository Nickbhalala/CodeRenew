// Behavior tests for the inventory module. CodeRenew runs these after each rewrite.
#include "inventory.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

static void test_add_and_find() {
    Inventory inv;
    assert(inv.add("A1", "Apple", 10, 0.5));
    assert(!inv.add("A1", "Apple again", 1, 1.0));  // duplicate SKU
    assert(!inv.add("B1", "Bad", -1, 1.0));         // negative quantity
    assert(inv.count() == 1);
    assert(inv.find("A1") != 0 && inv.find("A1")->name == "Apple");
    assert(inv.find("missing") == 0);
}

static void test_remove_keeps_order() {
    Inventory inv;
    inv.add("A", "a", 1, 1);
    inv.add("B", "b", 1, 1);
    inv.add("C", "c", 1, 1);
    assert(inv.remove("A"));
    assert(!inv.remove("A"));
    assert(inv.count() == 2);
    char* r = inv.report();
    assert(std::strcmp(r, "B x1\nC x1\n") == 0);  // remaining items keep their order
    std::free(r);
}

static void test_value_and_low_stock() {
    Inventory inv;
    inv.add("P", "Pen", 3, 1.25);
    inv.add("N", "Notebook", 20, 2.0);
    assert(std::fabs(inv.totalValue() - 43.75) < 1e-9);
    NameList low = inv.lowStock();
    assert(low.size() == 1 && low[0] == "Pen");
}

static void test_capacity() {
    Inventory inv;
    char sku[16];
    for (int i = 0; i < MAX_ITEMS; i++) {
        std::snprintf(sku, sizeof sku, "S%d", i);
        assert(inv.add(sku, "x", 1, 1));
    }
    assert(!inv.add("one-more", "x", 1, 1));
}

int main() {
    test_add_and_find();
    test_remove_keeps_order();
    test_value_and_low_stock();
    test_capacity();
    std::puts("all inventory tests passed");
    return 0;
}
